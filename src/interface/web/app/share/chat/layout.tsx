import type { Metadata } from "next";
import "../../globals.css";
import { APP_URL, ASSETS_URL } from "@/app/common/config";

export const metadata: Metadata = {
    title: "Apollos AI - Ask Anything",
    description:
        "Ask anything. Research answers from across the internet and your documents, draft messages, summarize documents, generate paintings and chat with personal agents.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apollos AI",
        title: "Apollos AI - Ask Anything",
        description:
            "Ask anything. Research answers from across the internet and your documents, draft messages, summarize documents, generate paintings and chat with personal agents.",
        url: `${APP_URL}/chat`,
        type: "website",
        images: [
            {
                url: `${ASSETS_URL}/apollos_hero.png`,
                width: 940,
                height: 525,
            },
            {
                url: `${ASSETS_URL}/apollos_lantern_256x256.png`,
                width: 256,
                height: 256,
            },
        ],
    },
};

export default function ChildLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <>
            {children}
            <script
                dangerouslySetInnerHTML={{
                    __html: `window.EXCALIDRAW_ASSET_PATH = '${ASSETS_URL}/@excalidraw/excalidraw/dist/';`,
                }}
            />
        </>
    );
}
