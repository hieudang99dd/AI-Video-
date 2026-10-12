import "./styles.css";
export const metadata = { title: "CineVideo", description: "Image-to-cinematic-video Core MVP" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="vi"><body>{children}</body></html>;
}
