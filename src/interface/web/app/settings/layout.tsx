import type { Metadata } from "next";
import "../globals.css";
import { Toaster } from "@/components/ui/toaster";
import { ChatwootWidget } from "../components/chatWoot/ChatwootWidget";
import { APP_URL, ASSETS_URL } from "@/app/common/config";

export const metadata: Metadata = {
    title: "Apollos AI - Settings",
    description: "Configure Apollos to get personalized, deeper assistance.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apollos AI",
        title: "Apollos AI - Settings",
        description: "Setup, configure, and personalize Apollos, your AI research assistant.",
        url: `${APP_URL}/settings`,
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
            <Toaster />
            <ChatwootWidget />
        </>
    );
}
