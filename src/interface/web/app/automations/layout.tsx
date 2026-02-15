import type { Metadata } from "next";
import { Toaster } from "@/components/ui/toaster";

import "../globals.css";
import { APP_URL, ASSETS_URL } from "@/app/common/config";

export const metadata: Metadata = {
    title: "Apollos AI - Automations",
    description:
        "Use Apollos Automations to get tailored research and event based notifications directly in your inbox.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apollos AI",
        title: "Apollos AI - Automations",
        description:
            "Use Apollos Automations to get tailored research and event based notifications directly in your inbox.",
        url: `${APP_URL}/automations`,
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
        </>
    );
}
