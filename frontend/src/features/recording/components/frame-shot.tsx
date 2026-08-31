"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import type { Media } from "@/features/recording/api";

/**
 * The screen the operator was looking at when they made this gesture.
 *
 * A thumbnail rather than the whole picture, because a timeline of full
 * screenshots is a timeline nobody scrolls. Clicking one opens it — reading a
 * step's prose and wanting to see what was actually on screen is the single
 * most common thing a reviewer does here.
 */
export function FrameShot({ shot, label }: { shot: Media | undefined; label: string }) {
  const [open, setOpen] = useState(false);
  if (!shot) return null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="focus-visible:ring-ring block shrink-0 overflow-hidden rounded-md border focus-visible:ring-2 focus-visible:outline-none"
        aria-label={`Screen at ${label}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={shot.url}
          alt={`Screen at ${label}`}
          loading="lazy"
          className="h-24 w-40 bg-white object-cover object-top"
        />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-5xl">
          <DialogTitle className="text-base font-normal">{label}</DialogTitle>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={shot.url}
            alt={`Screen at ${label}`}
            className="max-h-[75vh] w-full rounded-md border bg-white object-contain"
          />
        </DialogContent>
      </Dialog>
    </>
  );
}

/** The screenshots of a recording, by the frame each one illustrates. */
export function shotsByFrame(media: Media[] | undefined): Map<number, Media> {
  const byFrame = new Map<number, Media>();
  for (const item of media ?? []) {
    if (item.kind !== "screenshot" || item.frame_index === null) continue;
    byFrame.set(item.frame_index, item);
  }
  return byFrame;
}
