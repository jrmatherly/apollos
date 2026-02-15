import type { Metadata } from "next";
import { Toaster } from "@/components/ui/toaster";

import "../globals.css";

export const metadata: Metadata = {
    title: "Apollos AI - Automations",
    description:
        "Use Apolloslos Automations to get tailored research and event based notifications directly in your inbox.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apolloslos AI",
        title: "Apolloslos AI - Automations",
        description:
            "Use Apolloslos Automations to get tailored research and event based notifications directly in your inbox.",
        url: "https://app.apollos.dev/automations",
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
        </>
    );
}
