"use client";

import { useEffect, useState } from "react";
import { CoverScreen } from "@/components/sections/CoverScreen";
import { HeroNames } from "@/components/sections/HeroNames";
import { Countdown } from "@/components/sections/Countdown";
import { CoupleInfo } from "@/components/sections/CoupleInfo";
import { EventDetails } from "@/components/sections/EventDetails";
import { LocationMap } from "@/components/sections/LocationMap";
import { LoveStory } from "@/components/sections/LoveStory";
import { Gallery } from "@/components/sections/Gallery";
import { RsvpForm } from "@/components/sections/RsvpForm";
import { WishesWall } from "@/components/sections/WishesWall";
import { DigitalGift } from "@/components/sections/DigitalGift";
import { Closing } from "@/components/sections/Closing";
import { MusicPlayer } from "@/components/sections/MusicPlayer";

export default function Home() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      document.body.classList.add("no-scroll");
    } else {
      document.body.classList.remove("no-scroll");
      window.scrollTo({ top: 0, behavior: "instant" });
    }
    return () => document.body.classList.remove("no-scroll");
  }, [isOpen]);

  return (
    <main className="relative">
      {!isOpen && <CoverScreen onOpen={() => setIsOpen(true)} />}

      <div
        className={`transition-opacity duration-700 ${
          isOpen ? "opacity-100" : "opacity-0"
        }`}
      >
        <HeroNames />
        <Countdown />
        <CoupleInfo />
        <EventDetails />
        <LocationMap />
        <LoveStory />
        <Gallery />
        <RsvpForm />
        <WishesWall />
        <DigitalGift />
        <Closing />
      </div>

      <MusicPlayer shouldPlay={isOpen} />
    </main>
  );
}
