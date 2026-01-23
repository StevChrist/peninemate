import Header from "@/components/layout/Header";
import Image from "next/image";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <Header />

      {/* Main Content - Centered vertically */}
      <main className="flex-1 flex flex-col justify-center container mx-auto px-4 py-8 max-w-5xl">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-oswald font-medium text-highlight">
            /About
          </h1>
        </div>

        {/* Description */}
        <div className="text-white text-base leading-relaxed text-justify mb-12 max-w-4xl mx-auto">
          <p>
            PenineMate is a non-commercial, academic AI-powered movie assistant
            developed for educational and portfolio purposes. The application
            leverages multiple data sources, including the TMDb API for movie
            metadata, cast information, and popularity metrics, as well as Box
            Office and MovieLens datasets to enhance movie question answering and
            semantic-based recommendation features. PenineMate is built using{" "}
            <strong>PostgreSQL</strong> for structured data storage and{" "}
            <strong>FAISS</strong> for efficient vector similarity search, while
            its language understanding and reasoning capabilities are powered by
            the <strong>Llama 3.1 8B Instruct</strong> large language model,
            deployed in a quantized Q4 configuration for optimized performance.
          </p>
        </div>

        {/* Logo Section */}
        <div className="flex justify-center items-center gap-16">
          {/* Kaggle Logo - Using SVG file */}
          <a
            href="https://www.kaggle.com"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-transform duration-300 hover:scale-110"
          >
            <Image
              src="/kaggle.svg"
              alt="Kaggle Logo"
              width={120}
              height={60}
              className="h-16 w-auto"
            />
          </a>

          {/* TMDb Logo - Using SVG file */}
          <a
            href="https://www.themoviedb.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-transform duration-300 hover:scale-110"
          >
            <Image
              src="/tdmb.svg"
              alt="TMDb Logo"
              width={120}
              height={60}
              className="h-16 w-auto"
            />
          </a>

          {/* PEN Logo - Using PNG file */}
          <a
            href="https://stevchrist.vercel.app/"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-transform duration-300 hover:scale-110"
          >
            <Image
              src="/logo_pen.png"
              alt="PEN Logo"
              width={120}
              height={60}
              className="h-16 w-auto"
            />
          </a>
        </div>
      </main>

      {/* Footer - Always at bottom */}
      <footer className="py-6 text-center text-gray-400 text-sm">
        <p>2026 | V1.0 | Pen.</p>
      </footer>
    </div>
  );
}
