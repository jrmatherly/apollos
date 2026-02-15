import type { Metadata } from "next";

import "../globals.css";
import { APP_URL, ASSETS_URL } from "@/app/common/config";

export const metadata: Metadata = {
    title: "Apollos AI - Search",
    description:
        "Find anything in documents you've shared with Apollos using natural language queries.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apollos AI",
        title: "Apollos AI - Search",
        description: "Your Second Brain.",
        url: `${APP_URL}/search`,
        type: "website",
        images: [
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
    return <>{children}</>;
}
