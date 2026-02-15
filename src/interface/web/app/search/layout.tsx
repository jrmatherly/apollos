import type { Metadata } from "next";

import "../globals.css";

export const metadata: Metadata = {
    title: "Apollos AI - Search",
    description:
        "Find anything in documents you've shared with Apolloslos using natural language queries.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apolloslos AI",
        title: "Apolloslos AI - Search",
        description: "Your Second Brain.",
        url: "https://app.apollos.dev/search",
        type: "website",
        images: [
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
    return <>{children}</>;
}
