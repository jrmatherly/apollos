import asyncio
import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Union

from asgiref.sync import sync_to_async
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    Header,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel
from starlette.authentication import requires

from apollos.database import adapters
from apollos.database.adapters import (
    EntryAdapters,
    FileObjectAdapters,
    get_user_github_config,
    get_user_notion_config,
)
from apollos.database.models import ApollosUser, GithubConfig, GithubRepoConfig, NotionConfig, Team, TeamMembership
from apollos.database.models import Entry as DbEntry
from apollos.processor.content.docx.docx_to_entries import DocxToEntries
from apollos.processor.content.pdf.pdf_to_entries import PdfToEntries
from apollos.routers.auth_helpers import ROLE_HIERARCHY, aget_user_role_in_team
from apollos.routers.helpers import (
    ApiIndexedDataLimiter,
    CommonQueryParams,
    configure_content,
    get_file_content,
    get_user_config,
    update_telemetry_state,
)
from apollos.utils import state
from apollos.utils.rawconfig import GithubContentConfig, NotionContentConfig
from apollos.utils.state import SearchType

logger = logging.getLogger(__name__)

api_content = APIRouter()

executor = ThreadPoolExecutor()


class File(BaseModel):
    path: str
    content: Union[str, bytes]


class IndexBatchRequest(BaseModel):
    files: list[File]


class IndexerInput(BaseModel):
    org: Optional[dict[str, str]] = None
    markdown: Optional[dict[str, str]] = None
    pdf: Optional[dict[str, bytes]] = None
    plaintext: Optional[dict[str, str]] = None
    image: Optional[dict[str, bytes]] = None
    docx: Optional[dict[str, bytes]] = None


async def run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)


async def _check_delete_permission_for_entries(user: ApollosUser, entries_qs) -> None:
    """Check that user has permission to delete the given entries queryset.

    Permission rules:
    - Private entries: only the owning user can delete (already filtered by user in adapters)
    - Team entries: requires team_lead role (or org admin)
    - Org entries: requires org admin

    Raises HTTPException(403) if the user lacks permission for any entry visibility level.
    """
    is_admin = user.is_org_admin or user.is_staff

    # Check for org-visible entries
    has_org_entries = await entries_qs.filter(visibility=DbEntry.Visibility.ORGANIZATION).aexists()
    if has_org_entries and not is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete org-wide content")

    # Check for team-visible entries
    if not is_admin:
        team_entries = entries_qs.filter(visibility=DbEntry.Visibility.TEAM)
        if await team_entries.aexists():
            # Get distinct teams for these entries
            team_ids = await sync_to_async(list)(team_entries.values_list("team_id", flat=True).distinct())
            for team_id in team_ids:
                if team_id is None:
                    continue
                try:
                    team = await sync_to_async(Team.objects.get)(id=team_id)
                except Team.DoesNotExist:
                    continue
                role = await aget_user_role_in_team(user, team)
                if role is None or ROLE_HIERARCHY.get(role, 0) < ROLE_HIERARCHY["team_lead"]:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Requires team_lead role or higher in team '{team.name}' to delete team content",
                    )


@api_content.put("")
@requires(["authenticated"])
async def put_content(
    request: Request,
    files: List[UploadFile] = [],
    t: Optional[Union[state.SearchType, str]] = state.SearchType.All,
    client: Optional[str] = None,
    user_agent: Optional[str] = Header(None),
    referer: Optional[str] = Header(None),
    host: Optional[str] = Header(None),
    visibility: str = Form(default="private"),
    team_slug: Optional[str] = Form(default=None),
    indexed_data_limiter: ApiIndexedDataLimiter = Depends(
        ApiIndexedDataLimiter(
            incoming_entries_size_limit=50,
            subscribed_incoming_entries_size_limit=100,
            total_entries_size_limit=50,
            subscribed_total_entries_size_limit=500,
        )
    ),
):
    return await indexer(request, files, t, True, client, user_agent, referer, host, visibility, team_slug)


@api_content.patch("")
@requires(["authenticated"])
async def patch_content(
    request: Request,
    files: List[UploadFile] = [],
    t: Optional[Union[state.SearchType, str]] = state.SearchType.All,
    client: Optional[str] = None,
    user_agent: Optional[str] = Header(None),
    referer: Optional[str] = Header(None),
    host: Optional[str] = Header(None),
    visibility: str = Form(default="private"),
    team_slug: Optional[str] = Form(default=None),
    indexed_data_limiter: ApiIndexedDataLimiter = Depends(
        ApiIndexedDataLimiter(
            incoming_entries_size_limit=50,
            subscribed_incoming_entries_size_limit=100,
            total_entries_size_limit=50,
            subscribed_total_entries_size_limit=500,
        )
    ),
):
    return await indexer(request, files, t, False, client, user_agent, referer, host, visibility, team_slug)


@api_content.get("/github", response_class=Response)
@requires(["authenticated"])
def get_content_github(request: Request) -> Response:
    user = request.user.object
    user_config = get_user_config(user, request)
    del user_config["request"]

    current_github_config = get_user_github_config(user)

    if current_github_config:
        raw_repos = current_github_config.githubrepoconfig.all()
        repos = []
        for repo in raw_repos:
            repos.append(
                GithubRepoConfig(
                    name=repo.name,
                    owner=repo.owner,
                    branch=repo.branch,
                )
            )
        current_config = GithubContentConfig(
            pat_token=current_github_config.pat_token,
            repos=repos,
        )
        current_config = json.loads(current_config.json())
    else:
        current_config = {}  # type: ignore

    user_config["current_config"] = current_config

    # Return config data as a JSON response
    return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)


@api_content.get("/notion", response_class=Response)
@requires(["authenticated"])
def get_content_notion(request: Request) -> Response:
    user = request.user.object
    user_config = get_user_config(user, request)
    del user_config["request"]

    current_notion_config = get_user_notion_config(user)
    token = current_notion_config.token if current_notion_config else ""
    current_config = NotionContentConfig(token=token)
    current_config = json.loads(current_config.model_dump_json())

    user_config["current_config"] = current_config

    # Return config data as a JSON response
    return Response(content=json.dumps(user_config), media_type="application/json", status_code=200)


@api_content.post("/github", status_code=200)
@requires(["authenticated"])
async def set_content_github(
    request: Request,
    updated_config: Union[GithubContentConfig, None],
    client: Optional[str] = None,
):
    user = request.user.object

    try:
        await adapters.set_user_github_config(
            user=user,
            pat_token=updated_config.pat_token,
            repos=updated_config.repos,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set Github config")

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="set_content_config",
        client=client,
        metadata={"content_type": "github"},
    )

    return {"status": "ok"}


@api_content.post("/notion", status_code=200)
@requires(["authenticated"])
async def set_content_notion(
    request: Request,
    background_tasks: BackgroundTasks,
    updated_config: Union[NotionContentConfig, None],
    client: Optional[str] = None,
):
    user = request.user.object

    try:
        await adapters.set_notion_config(
            user=user,
            token=updated_config.token,
        )
    except Exception as e:
        logger.error(e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set Notion config")

    if updated_config.token:
        # Trigger an async job to configure_content. Let it run without blocking the response.
        background_tasks.add_task(run_in_executor, configure_content, user, {}, False, SearchType.Notion)

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="set_content_config",
        client=client,
        metadata={"content_type": "notion"},
    )

    return {"status": "ok"}


@api_content.delete("/file", status_code=201)
@requires(["authenticated"])
async def delete_content_files(
    request: Request,
    filename: str,
    client: Optional[str] = None,
):
    user = request.user.object

    # RBAC: Check permission based on entry visibility before deleting
    entries_qs = DbEntry.objects.filter(user=user, file_path=filename)
    await _check_delete_permission_for_entries(user, entries_qs)

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="delete_file",
        client=client,
    )

    await EntryAdapters.adelete_entry_by_file(user, filename)

    await FileObjectAdapters.adelete_file_object_by_name(user, filename)

    return {"status": "ok"}


class DeleteFilesRequest(BaseModel):
    files: List[str]


@api_content.delete("/files", status_code=201)
@requires(["authenticated"])
async def delete_content_file(
    request: Request,
    files: DeleteFilesRequest,
    client: Optional[str] = None,
):
    user = request.user.object

    # RBAC: Check permission based on entry visibility before deleting
    entries_qs = DbEntry.objects.filter(user=user, file_path__in=files.files)
    await _check_delete_permission_for_entries(user, entries_qs)

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="delete_file",
        client=client,
    )

    deleted_count = await EntryAdapters.adelete_entries_by_filenames(user, files.files)
    for file in files.files:
        await FileObjectAdapters.adelete_file_object_by_name(user, file)

    return {"status": "ok", "deleted_count": deleted_count}


@api_content.get("/size", response_model=Dict[str, int])
@requires(["authenticated"])
async def get_content_size(request: Request, common: CommonQueryParams, client: Optional[str] = None):
    user = request.user.object
    indexed_data_size_in_mb = await sync_to_async(EntryAdapters.get_size_of_indexed_data_in_mb)(user)
    return Response(
        content=json.dumps({"indexed_data_size_in_mb": math.ceil(indexed_data_size_in_mb)}),
        media_type="application/json",
        status_code=200,
    )


@api_content.get("/types", response_model=List[str])
@requires(["authenticated"])
def get_content_types(request: Request, client: Optional[str] = None):
    user = request.user.object
    all_content_types = {s.value for s in SearchType}
    configured_content_types = set(EntryAdapters.get_unique_file_types(user))
    configured_content_types |= {"all"}

    return list(configured_content_types & all_content_types)


@api_content.get("/files", response_model=Dict[str, str])
@requires(["authenticated"])
async def get_all_files(
    request: Request, client: Optional[str] = None, truncated: Optional[bool] = True, page: int = 0
):
    user = request.user.object

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="get_all_filenames",
        client=client,
    )

    files_data = []
    page_size = 10

    file_objects = await FileObjectAdapters.aget_all_file_objects(user, start=page * page_size, limit=page_size)

    num_pages = await FileObjectAdapters.aget_number_of_pages(user, page_size)

    for file_object in file_objects:
        files_data.append(
            {
                "file_name": file_object.file_name,
                "raw_text": file_object.raw_text[:1000] if truncated else file_object.raw_text,
                "updated_at": str(file_object.updated_at),
            }
        )

    data_packet = {
        "files": files_data,
        "num_pages": num_pages,
    }

    return Response(content=json.dumps(data_packet), media_type="application/json", status_code=200)


@api_content.get("/file", response_model=Dict[str, str])
@requires(["authenticated"])
async def get_file_object(
    request: Request,
    file_name: str,
    client: Optional[str] = None,
):
    user = request.user.object

    file_object = (await FileObjectAdapters.aget_file_objects_by_name(user, file_name))[0]
    if not file_object:
        return Response(
            content=json.dumps({"error": "File not found"}),
            media_type="application/json",
            status_code=404,
        )

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="get_file",
        client=client,
    )

    return Response(
        content=json.dumps(
            {"id": file_object.id, "file_name": file_object.file_name, "raw_text": file_object.raw_text}
        ),
        media_type="application/json",
        status_code=200,
    )


@api_content.delete("/type/{content_type}", status_code=200)
@requires(["authenticated"])
async def delete_content_type(
    request: Request,
    content_type: str,
    client: Optional[str] = None,
):
    user = request.user.object
    if content_type not in {s.value for s in SearchType}:
        raise ValueError(f"Unsupported content type: {content_type}")

    # RBAC: Check permission based on entry visibility before deleting
    if content_type == "all":
        entries_qs = DbEntry.objects.filter(user=user)
    else:
        entries_qs = DbEntry.objects.filter(user=user, file_type=content_type)
    await _check_delete_permission_for_entries(user, entries_qs)

    if content_type == "all":
        await EntryAdapters.adelete_all_entries(user)
    else:
        # Delete file objects of the given type
        file_list = await sync_to_async(list)(EntryAdapters.get_all_filenames_by_type(user, content_type))  # type: ignore[call-arg]
        await FileObjectAdapters.adelete_file_objects_by_names(user, file_list)
        # Delete entries of the given type
        await EntryAdapters.adelete_all_entries(user, file_type=content_type)

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="delete_content_config",
        client=client,
        metadata={"content_type": content_type},
    )

    return {"status": "ok"}


@api_content.get("/{content_source}", response_model=List[str])
@requires(["authenticated"])
async def get_content_source(
    request: Request,
    content_source: str,
    client: Optional[str] = None,
):
    user = request.user.object

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="get_all_filenames",
        client=client,
    )

    return await sync_to_async(list)(EntryAdapters.get_all_filenames_by_source(user, content_source))  # type: ignore[call-arg]


@api_content.delete("/source/{content_source}", status_code=200)
@requires(["authenticated"])
async def delete_content_source(
    request: Request,
    content_source: str,
    client: Optional[str] = None,
):
    user = request.user.object

    # RBAC: Check permission based on entry visibility before deleting
    entries_qs = DbEntry.objects.filter(user=user, file_source=content_source)
    await _check_delete_permission_for_entries(user, entries_qs)

    content_object = map_config_to_object(content_source)
    if content_object is None:
        raise ValueError(f"Invalid content source: {content_source}")
    elif content_object != "Computer":
        await content_object.objects.filter(user=user).adelete()
    else:
        # Delete file objects from the given source
        file_list = await sync_to_async(list)(EntryAdapters.get_all_filenames_by_source(user, content_source))  # type: ignore[call-arg]
        await FileObjectAdapters.adelete_file_objects_by_names(user, file_list)
    # Delete entries from the given source
    await EntryAdapters.adelete_all_entries(user, file_source=content_source)

    if content_source == DbEntry.EntrySource.NOTION:
        await NotionConfig.objects.filter(user=user).adelete()
    elif content_source == DbEntry.EntrySource.GITHUB:
        await GithubConfig.objects.filter(user=user).adelete()

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="delete_content_config",
        client=client,
        metadata={"content_source": content_source},
    )

    return {"status": "ok"}


@api_content.post("/convert", status_code=200)
@requires(["authenticated"])
async def convert_documents(
    request: Request,
    files: List[UploadFile],
    client: Optional[str] = None,
):
    MAX_FILE_SIZE_MB = 10  # 10MB limit
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    converted_files = []
    supported_files = ["org", "markdown", "pdf", "plaintext", "docx"]

    for file in files:
        # Check file size first
        file_size = 0
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Reset file pointer

        if file_size > MAX_FILE_SIZE_BYTES:
            logger.warning(
                f"Skipped converting oversized file ({file_size / 1024 / 1024:.1f}MB) sent by {client} client: {file.filename}"
            )
            continue

        file_data = get_file_content(file)
        if file_data.file_type in supported_files:
            extracted_content = (
                file_data.content.decode(file_data.encoding) if file_data.encoding else file_data.content
            )

            if file_data.file_type == "docx":
                entries_per_page = DocxToEntries.extract_text(file_data.content)
                annotated_pages = [
                    f"Page {index} of {file_data.name}:\n\n{entry}" for index, entry in enumerate(entries_per_page)
                ]
                extracted_content = "\n".join(annotated_pages)

            elif file_data.file_type == "pdf":
                entries_per_page = PdfToEntries.extract_text(file_data.content)
                annotated_pages = [
                    f"Page {index} of {file_data.name}:\n\n{entry}" for index, entry in enumerate(entries_per_page)
                ]
                extracted_content = "\n".join(annotated_pages)
            else:
                # Convert content to string
                extracted_content = extracted_content.decode("utf-8")

            # Calculate size in bytes. Some of the content might be in bytes, some in str.
            if isinstance(extracted_content, str):
                size_in_bytes = len(extracted_content.encode("utf-8"))
            elif isinstance(extracted_content, bytes):
                size_in_bytes = len(extracted_content)
            else:
                size_in_bytes = 0
                logger.warning(f"Unexpected content type: {type(extracted_content)}")

            converted_files.append(
                {
                    "name": file_data.name,
                    "content": extracted_content,
                    "file_type": file_data.file_type,
                    "size": size_in_bytes,
                }
            )
        else:
            logger.warning(f"Skipped converting unsupported file type sent by {client} client: {file.filename}")

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="convert_documents",
        client=client,
    )

    return Response(content=json.dumps(converted_files), media_type="application/json", status_code=200)


async def indexer(
    request: Request,
    files: list[UploadFile],
    t: Optional[Union[state.SearchType, str]] = state.SearchType.All,
    regenerate: bool = False,
    client: Optional[str] = None,
    user_agent: Optional[str] = Header(None),
    referer: Optional[str] = Header(None),
    host: Optional[str] = Header(None),
    visibility: str = "private",
    team_slug: Optional[str] = None,
):
    user = request.user.object

    # Validate visibility parameter
    if visibility not in ("private", "team", "org"):
        raise HTTPException(status_code=400, detail="visibility must be 'private', 'team', or 'org'")
    if visibility == "team" and not team_slug:
        raise HTTPException(status_code=400, detail="team_slug is required when visibility is 'team'")
    if visibility == "org" and not (user.is_org_admin or user.is_staff):
        raise HTTPException(status_code=403, detail="Only admins can upload org-wide content")

    # Resolve team if needed
    resolved_team = None
    if visibility == "team" and team_slug:
        try:
            resolved_team = await sync_to_async(Team.objects.get)(slug=team_slug)
        except Team.DoesNotExist:
            raise HTTPException(status_code=404, detail=f"Team '{team_slug}' not found")
        # Verify user is member of the team (admins bypass)
        is_member = await sync_to_async(TeamMembership.objects.filter(user=user, team=resolved_team).exists)()
        if not is_member and not (user.is_org_admin or user.is_staff):
            raise HTTPException(status_code=403, detail="You are not a member of this team")

    method = "regenerate" if regenerate else "sync"
    index_files: Dict[str, Dict[str, str]] = {
        "org": {},
        "markdown": {},
        "pdf": {},
        "plaintext": {},
        "image": {},
        "docx": {},
    }
    try:
        logger.info(f"📬 Updating content index via API call by {client} client")
        for file in files:
            file_data = get_file_content(file)
            if file_data.file_type in index_files:
                index_files[file_data.file_type][file_data.name] = (
                    file_data.content.decode(file_data.encoding) if file_data.encoding else file_data.content
                )
            else:
                logger.debug(f"Skipped indexing unsupported file type sent by {client} client: {file_data.name}")

        indexer_input = IndexerInput(
            org=index_files["org"],
            markdown=index_files["markdown"],
            pdf=index_files["pdf"],
            plaintext=index_files["plaintext"],
            image=index_files["image"],
            docx=index_files["docx"],
        )

        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            configure_content,
            user,
            indexer_input.model_dump(),
            regenerate,
            t,
            visibility,
            resolved_team,
        )
        if not success:
            raise RuntimeError(f"Failed to {method} {t} data sent by {client} client into content index")
        logger.info(f"Finished {method} {t} data sent by {client} client into content index")
    except Exception as e:
        logger.error(f"Failed to {method} {t} data sent by {client} client into content index: {e}", exc_info=True)
        logger.error(
            f"🚨 Failed to {method} {t} data sent by {client} client into content index: {e}",
            exc_info=True,
        )
        return Response(content="Failed", status_code=500)

    indexing_metadata = {
        "num_org": len(index_files["org"]),
        "num_markdown": len(index_files["markdown"]),
        "num_pdf": len(index_files["pdf"]),
        "num_plaintext": len(index_files["plaintext"]),
        "num_image": len(index_files["image"]),
        "num_docx": len(index_files["docx"]),
    }

    update_telemetry_state(
        request=request,
        telemetry_type="api",
        api="index/update",
        client=client,
        user_agent=user_agent,
        referer=referer,
        host=host,
        metadata=indexing_metadata,
    )

    logger.info(f"📪 Content index updated via API call by {client} client")

    indexed_filenames = ",".join(file for ctype in index_files for file in index_files[ctype]) or ""
    return Response(content=indexed_filenames, status_code=200)


@api_content.post("/share")
@requires(["authenticated"])
async def share_content(request: Request):
    """Promote personal content to team or org visibility."""
    user = request.user.object
    body = await request.json()
    file_path = body.get("file_path")
    target_visibility = body.get("visibility")  # "team" or "org"
    target_team_slug = body.get("team_slug")  # Required for "team"

    if not file_path or not target_visibility:
        raise HTTPException(status_code=400, detail="file_path and visibility are required")

    if target_visibility not in ("team", "org"):
        raise HTTPException(status_code=400, detail="visibility must be 'team' or 'org'")

    # Permission checks
    if target_visibility == "org" and not (user.is_org_admin or user.is_staff):
        raise HTTPException(status_code=403, detail="Only admins can share to organization")

    target_team = None
    if target_visibility == "team":
        if not target_team_slug:
            raise HTTPException(status_code=400, detail="team_slug required for team sharing")
        try:
            target_team = await sync_to_async(Team.objects.get)(slug=target_team_slug)
        except Team.DoesNotExist:
            raise HTTPException(status_code=404, detail="Team not found")
        # Verify user is member of this team
        is_member = await sync_to_async(TeamMembership.objects.filter(user=user, team=target_team).exists)()
        if not is_member and not (user.is_org_admin or user.is_staff):
            raise HTTPException(status_code=403, detail="You are not a member of this team")

    # Update entry visibility
    update_kwargs = {"visibility": target_visibility, "shared_by": user}
    if target_team:
        update_kwargs["team"] = target_team

    count = await sync_to_async(DbEntry.objects.filter(user=user, file_path=file_path).update)(**update_kwargs)

    if count == 0:
        raise HTTPException(status_code=404, detail="No entries found for this file")

    return {"status": "shared", "count": count, "visibility": target_visibility}


def map_config_to_object(content_source: str):
    if content_source == DbEntry.EntrySource.GITHUB:
        return GithubConfig
    if content_source == DbEntry.EntrySource.NOTION:
        return NotionConfig
    if content_source == DbEntry.EntrySource.COMPUTER:
        return "Computer"
