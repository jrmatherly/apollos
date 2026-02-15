import type { Metadata } from "next";
import "../globals.css";
import { Toaster } from "@/components/ui/toaster";

export const metadata: Metadata = {
    title: "Apollos AI - Chat",
    description:
        "Ask anything. Research answers from across the internet and your documents, draft messages, summarize documents, generate paintings and chat with personal agents.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apolloslos AI",
        title: "Apolloslos AI - Chat",
        description:
            "Ask anything. Research answers from across the internet and your documents, draft messages, summarize documents, generate paintings and chat with personal agents.",
        url: "https://app.apollos.dev/chat",
        type: "website",
        images: [
            {
                url: "https://assets.apollos.dev/apollos_hero.png",
                width: 940,
                height: 525,
            },
            {
                url: "https://assets.apollos.dev/apollos_lantern_256x256.png",
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
            <Toaster />
            <script
                dangerouslySetInnerHTML={{
                    __html: `window.EXCALIDRAW_ASSET_PATH = 'https://assets.apollos.dev/@excalidraw/excalidraw/dist/';`,
                }}
            />
        </>
    );
}
