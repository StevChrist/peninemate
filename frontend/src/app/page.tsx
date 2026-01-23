"use client";

import { useRouter } from "next/navigation";
import Header from "@/components/layout/Header";
import SearchInput from "@/components/ui/SearchInput";

export default function Home() {
  const router = useRouter();

  const handleSearch = (query: string) => {
    router.push(`/ask?q=${encodeURIComponent(query)}`);
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="flex flex-col items-center justify-center min-h-screen px-clear">
        {/* Hero Section */}
        <div className="text-center space-y-6 w-full flex flex-col items-center">
          <h1 className="text-6xl md:text-7xl font-oswald font-medium">
            Welcome to{" "}
            <span className="text-highlight">PenineMate</span>
          </h1>
          
          <p className="text-xl md:text-2xl text-text/80 font-inter">
            what do you want film want to you know?
          </p>
          
          {/* Search Box - Centered */}
          <div className="pt-2 w-full flex justify-center">
            <SearchInput 
              placeholder="the film whose ship sank"
              onSubmit={handleSearch}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
