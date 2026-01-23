import Link from "next/link";
import Image from "next/image";

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-sm">
      <nav className="px-clear py-6">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center">
            <Image
              src="/logo_pen.png"
              alt="PenineMate Logo"
              width={50}
              height={50}
              className="hover:opacity-80 transition-opacity"
              priority
            />
          </Link>

          {/* Navigation */}
          <div className="flex items-center gap-8">
            <Link
              href="/"
              className="text-text hover:text-highlight transition-colors font-inter"
            >
              Home
            </Link>
            <Link
              href="/ask"
              className="text-text hover:text-highlight transition-colors font-inter"
            >
              Ask Bot!
            </Link>
            <Link
              href="/recommendation"
              className="text-text hover:text-highlight transition-colors font-inter"
            >
              Recommendation
            </Link>
            <Link
              href="/about"
              className="text-text hover:text-highlight transition-colors font-inter"
            >
              About
            </Link>
          </div>
        </div>
      </nav>
    </header>
  );
}
