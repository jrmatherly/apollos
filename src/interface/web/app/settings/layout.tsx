import type { Metadata } from "next";
import "../globals.css";
import { Toaster } from "@/components/ui/toaster";
import { ChatwootWidget } from "../components/chatWoot/ChatwootWidget";

export const metadata: Metadata = {
    title: "Apollos AI - Settings",
    description: "Configure Apolloslos to get personalized, deeper assistance.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apolloslos AI",
        title: "Apolloslos AI - Settings",
        description: "Setup, configure, and personalize Apolloslos, your AI research assistant.",
        url: "https://app.apollos.dev/settings",
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
            <ChatwootWidget />
        </>
    );
}
