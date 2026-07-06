"use client";

import Header from "@/components/layout/Header";
import Image from "next/image";
import { useState } from "react";

export default function AboutPage() {
  const [selectedVersion, setSelectedVersion] = useState<"1.2.1" | "1.2.0" | "1.1.0">("1.2.1");

  const versionContent = {
    "1.2.1": {
      title: "Version 1.2.1 (Current)",
      llm: "OpenAI GPT-5-nano",
      embedding: "OpenAI text-embedding-3-small (1536 dimensions)",
      description: `PenineMate is a non-commercial, academic AI-powered movie assistant 
        developed for educational and portfolio purposes. The application leverages multiple 
        data sources, including the TMDb API for movie metadata, cast information, and 
        popularity metrics, as well as Box Office and MovieLens datasets to enhance movie 
        question answering and semantic-based recommendation features.`,
      architecture: `PenineMate is built using PostgreSQL for structured data storage and 
        FAISS for efficient vector similarity search. The system's language understanding 
        and reasoning capabilities are powered by OpenAI's GPT-5-nano model for natural 
        language processing and intent classification, while vector embeddings are generated 
        using OpenAI's text-embedding-3-small model (1536-dimensional) for semantic search 
        and similarity matching.`,
      updates: [
        "Language Model: OpenAI GPT-4o-mini → OpenAI GPT-5-nano",
        "Embedding Model: Sentence-Transformers (384d) → OpenAI text-embedding-3-small (1536d)",
        "Enhanced semantic search accuracy with 4x larger embedding dimensions",
        "Improved intent classification and natural language understanding",
        "Added franchise detection for 'How many X films?' type queries",
        "Better multilingual support for English and Indonesian conversations",
        "Optimized response generation with cloud-based LLM infrastructure"
      ]
    },
    "1.2.0": {
      title: "Version 1.2.0 (Previous)",
      llm: "OpenAI GPT-4o-mini",
      embedding: "OpenAI text-embedding-3-small (1536 dimensions)",
      description: `PenineMate is a non-commercial, academic AI-powered movie assistant 
        developed for educational and portfolio purposes. The application leverages multiple 
        data sources, including the TMDb API for movie metadata, cast information, and 
        popularity metrics, as well as Box Office and MovieLens datasets to enhance movie 
        question answering and semantic-based recommendation features.`,
      architecture: `PenineMate is built using PostgreSQL for structured data storage and 
        FAISS for efficient vector similarity search. The system's language understanding 
        and reasoning capabilities are powered by OpenAI's GPT-4o-mini model for natural 
        language processing and intent classification, while vector embeddings are generated 
        using OpenAI's text-embedding-3-small model (1536-dimensional) for semantic search 
        and similarity matching.`,
      updates: [
        "Language Model: Ollama Qwen 2.5 3B → OpenAI GPT-4o-mini",
        "Embedding Model: Sentence-Transformers (384d) → OpenAI text-embedding-3-small (1536d)",
        "Enhanced semantic search accuracy with 4x larger embedding dimensions",
        "Improved intent classification and natural language understanding",
        "Added franchise detection for 'How many X films?' type queries",
        "Better multilingual support for English and Indonesian conversations",
        "Optimized response generation with cloud-based LLM infrastructure"
      ]
    },
    "1.1.0": {
      title: "Version 1.1.0 (Previous)",
      llm: "Ollama Qwen 2.5 3B Instruct (Q4 quantized)",
      embedding: "Sentence-Transformers all-MiniLM-L6-v2 (384 dimensions)",
      description: `PenineMate Version 1.1.0 was the initial release featuring local 
        AI models for complete offline operation. This version focused on establishing 
        the core architecture and proof-of-concept functionality.`,
      architecture: `Built with PostgreSQL for data storage and FAISS for vector search. 
        Language understanding was powered by Qwen 2.5 3B Instruct model via Ollama, 
        deployed in a quantized Q4 configuration for optimized performance on local hardware. 
        Vector embeddings were generated using the sentence-transformers library with the 
        all-MiniLM-L6-v2 model (384-dimensional embeddings).`,
      updates: [
        "Initial RAG (Retrieval-Augmented Generation) architecture implementation",
        "Local LLM deployment using Ollama Qwen 2.5 3B for privacy-focused operation",
        "FAISS vector indexing with sentence-transformers embeddings",
        "Basic conversational Q&A functionality about movies",
        "PostgreSQL database integration with TMDb dataset",
        "Hybrid search combining keyword and semantic matching",
        "Movie recommendation system based on user preferences"
      ]
    }
  };

  const currentVersion = versionContent[selectedVersion];

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <Header />

      {/* Main Content */}
      <main className="flex-1 flex flex-col justify-center container mx-auto px-4 pt-24 pb-8 max-w-5xl">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-oswald font-medium text-highlight">
            /About
          </h1>
        </div>

        {/* Version Selector */}
        <div className="flex justify-center gap-4 mb-8">
          <button
            onClick={() => setSelectedVersion("1.2.1")}
            className={`px-6 py-2 rounded-lg font-medium transition-all duration-300 ${
              selectedVersion === "1.2.1"
                ? "bg-highlight text-background"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            v1.2.1 (Current)
          </button>
          <button
            onClick={() => setSelectedVersion("1.2.0")}
            className={`px-6 py-2 rounded-lg font-medium transition-all duration-300 ${
              selectedVersion === "1.2.0"
                ? "bg-highlight text-background"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            v1.2.0
          </button>
          <button
            onClick={() => setSelectedVersion("1.1.0")}
            className={`px-6 py-2 rounded-lg font-medium transition-all duration-300 ${
              selectedVersion === "1.1.0"
                ? "bg-highlight text-background"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            v1.1.0
          </button>
        </div>

        {/* Version Title */}
        <div className="text-center mb-6">
          <h2 className="text-2xl font-oswald font-medium text-highlight">
            {currentVersion.title}
          </h2>
        </div>

        {/* Description */}
        <div className="text-white text-base leading-relaxed text-justify mb-8 max-w-4xl mx-auto">
          <p className="mb-4">{currentVersion.description}</p>
          <p className="mb-6">{currentVersion.architecture}</p>
        </div>

        {/* Model Information Cards - UPDATED with 30% opacity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 max-w-4xl mx-auto">
          {/* LLM Model Card */}
          <div className="bg-gray-800/30 rounded-lg p-6 border border-gray-700/30 backdrop-blur-sm">
            <h3 className="text-highlight font-oswald text-xl mb-3">
              Language Model
            </h3>
            <p className="text-white text-sm leading-relaxed">
              <strong className="text-gray-300">Model:</strong> {currentVersion.llm}
            </p>
            <p className="text-gray-400 text-xs mt-2">
              Used for intent classification, query understanding, and natural language response generation
            </p>
          </div>

          {/* Embedding Model Card */}
          <div className="bg-gray-800/30 rounded-lg p-6 border border-gray-700/30 backdrop-blur-sm">
            <h3 className="text-highlight font-oswald text-xl mb-3">
              Embedding Model
            </h3>
            <p className="text-white text-sm leading-relaxed">
              <strong className="text-gray-300">Model:</strong> {currentVersion.embedding}
            </p>
            <p className="text-gray-400 text-xs mt-2">
              Used for semantic vector representation and similarity search in FAISS index
            </p>
          </div>
        </div>

        {/* Updates Section - UPDATED with 30% opacity */}
        <div className="bg-gray-800/30 rounded-lg p-6 border border-gray-700/30 backdrop-blur-sm mb-12 max-w-4xl mx-auto">
          <h3 className="text-highlight font-oswald text-xl mb-4">
            Updates:
          </h3>
          <ul className="space-y-2">
            {currentVersion.updates.map((item, index) => (
              <li key={index} className="text-white text-sm flex items-start">
                <span className="text-highlight mr-2 mt-1">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Status Note */}
        <div className="text-center mb-12">
          <p className="text-gray-400 text-sm italic">
            The project is already usable but still needs to be developed further.
          </p>
        </div>

        {/* Logo Section */}
        <div className="flex justify-center items-center gap-16 flex-wrap">
          {/* Kaggle Logo */}
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

          {/* TMDb Logo */}
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

          {/* PEN Logo */}
          <a
            href="https://stevchrist.site/"
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

      {/* Footer */}
      <footer className="py-6 text-center text-gray-400 text-sm">
        <p>2026 | V{selectedVersion} | Pen.</p>
      </footer>
    </div>
  );
}
