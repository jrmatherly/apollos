import type { Metadata } from "next";
import "../globals.css";

export const metadata: Metadata = {
    title: "Apollos AI - Agents",
    description:
        "Find or create agents with custom knowledge, tools and personalities to help address your specific needs.",
    icons: {
        icon: "/static/assets/icons/apollos_lantern.ico",
        apple: "/static/assets/icons/apollos_lantern_256x256.png",
    },
    openGraph: {
        siteName: "Apolloslos AI",
        title: "Apolloslos AI - Agents",
        description:
            "Find or create agents with custom knowledge, tools and personalities to help address your specific needs.",
        url: "https://app.apollos.dev/agents",
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
    return <>{children}</>;
}
