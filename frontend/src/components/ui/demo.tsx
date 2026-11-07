"use client";

import { Component } from "@/components/ui/animated-card";

const Demo = () => {
  return (
    <div className="flex h-full w-full items-center justify-center bg-white dark:bg-black">
      <div className="relative grid w-5/6 grid-cols-1 gap-4 p-2 md:grid-cols-2">
        <Component
          className="p-4"
          description="This is the best library for creating dynamic cards"
          title="EldoraUI"
        >
          You can also add content inside the card
        </Component>
        <Component
          className="p-4"
          description="How fast is it now to create cards"
          title="Is Just crazy"
        >
          If leave the card empty, it will still look good
        </Component>
        <Component
          description="I just have to copy paste the code and it instantly works"
          title="Amazing"
        />
        <Component
          description="I can't believe how easy it is to use"
          title="Unbelievable"
        />
      </div>
    </div>
  );
};

export default Demo;
