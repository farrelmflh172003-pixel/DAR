"use client";
import { ArrowUpRightIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";

export const useMouse = () => {
  const [mouse, setMouse] = useState<{
    elementX: number | null;
    elementY: number | null;
  }>({
    elementX: null,
    elementY: null,
  });
  const parentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      if (parentRef.current) {
        const { left, top } = parentRef.current.getBoundingClientRect();
        setMouse({
          elementX: event.clientX - left,
          elementY: event.clientY - top,
        });
      }
    };

    const handleMouseLeave = () => {
      setMouse({
        elementX: null,
        elementY: null,
      });
    };

    const currentRef = parentRef.current;
    if (currentRef) {
      currentRef.addEventListener("mousemove", handleMouseMove);
      currentRef.addEventListener("mouseleave", handleMouseLeave);
    }

    return () => {
      if (currentRef) {
        currentRef.removeEventListener("mousemove", handleMouseMove);
        currentRef.removeEventListener("mouseleave", handleMouseLeave);
      }
    };
  }, []);

  return [mouse, parentRef] as const;
};

export const Component = ({
  title,
  description,
  withArrow = false,
  circleSize = 400,
  className,
  children,
}: {
  title: string;
  description: string;
  withArrow?: boolean;
  circleSize?: number;
  children?: ReactNode;
  className?: string;
}) => {
  const [mouse, parentRef] = useMouse();

  return (
    <div
      className="group relative transform-gpu overflow-hidden rounded-[20px] bg-neutral-200/50 p-2 transition-transform hover:scale-[1.01] active:scale-90"
      ref={parentRef}
    >
      {withArrow && (
        <ArrowUpRightIcon className="absolute right-2 top-2 z-10 size-5 translate-y-4 text-neutral-700 opacity-0 transition-all group-hover:translate-y-0 group-hover:opacity-100" />
      )}
      <div
        className={cn(
          "absolute -translate-x-1/2 -translate-y-1/2 transform-gpu rounded-full transition-transform duration-500 group-hover:scale-[3]",
          mouse.elementX === null || mouse.elementY === null
            ? "opacity-0"
            : "opacity-100",
        )}
        style={{
          maskImage: `radial-gradient(${
            circleSize / 2
          }px circle at center, white, transparent)`,
          WebkitMaskImage: `radial-gradient(${
            circleSize / 2
          }px circle at center, white, transparent)`,
          width: `${circleSize}px`,
          height: `${circleSize}px`,
          left: `${mouse.elementX}px`,
          top: `${mouse.elementY}px`,
          background:
            "linear-gradient(135deg, #3BC4F2, #7A69F9,#F26378,#F5833F)",
        }}
      />
      <div className="absolute inset-px rounded-[19px] bg-white shadow-sm" />
      {children && (
        <div
          className={cn(
            "grid relative h-40 place-content-center overflow-hidden rounded-[15px] border border-neutral-200 bg-neutral-50",
            className,
          )}
        >
          {children}
        </div>
      )}
      <div className="relative px-4 pb-2 pt-4">
        <h3 className="text-lg font-bold text-neutral-900">
          {title}
        </h3>
        <p className="mt-2 text-neutral-700">
          {description}
        </p>
      </div>
    </div>
  );
};

export interface HubCardProps {
  id?: string;
  title: string;
  headerAction?: ReactNode;
  badge?: ReactNode;
  content?: ReactNode;
  children?: ReactNode;
  isSelected?: boolean;
  isSelectable?: boolean;
  selectionNumber?: number | null;
  onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
  className?: string;
  circleSize?: number;
}

export const HubAnimatedCard = ({
  id,
  title,
  headerAction,
  badge,
  content,
  children,
  isSelected = false,
  isSelectable = false,
  selectionNumber,
  onClick,
  className,
  circleSize = 400,
}: HubCardProps) => {
  const [mouse, parentRef] = useMouse();

  return (
    <div
      id={id}
      ref={parentRef}
      onClick={onClick}
      className={cn(
        "group relative transform-gpu overflow-hidden rounded-[20px] p-[2px] transition-all duration-200",
        isSelectable && "cursor-pointer hover:scale-[1.008] active:scale-[0.99]",
        isSelected
          ? "ring-2 ring-[#2563EB] shadow-[0_0_20px_rgba(37,99,235,0.35)] bg-[#2563EB]"
          : "bg-white/20 hover:bg-white/30",
        className
      )}
    >
      {/* Top-right corner sequence number notification badge */}
      {selectionNumber != null && selectionNumber > 0 && (
        <div
          className="card-selection-corner-badge"
          title={`Pilihan ke-${selectionNumber}`}
        >
          {selectionNumber}
        </div>
      )}

      {/* Animated gradient spotlight on mouse hover */}
      <div
        className={cn(
          "pointer-events-none absolute -translate-x-1/2 -translate-y-1/2 transform-gpu rounded-full transition-opacity duration-300",
          mouse.elementX === null || mouse.elementY === null
            ? "opacity-0"
            : "opacity-100"
        )}
        style={{
          maskImage: `radial-gradient(${
            circleSize / 2
          }px circle at center, white, transparent)`,
          WebkitMaskImage: `radial-gradient(${
            circleSize / 2
          }px circle at center, white, transparent)`,
          width: `${circleSize}px`,
          height: `${circleSize}px`,
          left: `${mouse.elementX ?? 0}px`,
          top: `${mouse.elementY ?? 0}px`,
          background:
            "linear-gradient(135deg, #3BC4F2, #7A69F9, #F26378, #F5833F)",
        }}
      />

      {/* Inner background layer: PURE WHITE CARD */}
      <div
        className="absolute inset-px rounded-[18px] bg-[#FFFFFF]"
        style={{
          boxShadow: '0 2px 10px rgba(0, 0, 0, 0.12)',
        }}
      />

      {/* Content container with BLACK TEXT */}
      <div
        className="relative z-10 flex h-full w-full flex-col justify-start"
        style={{ padding: '16px 20px', minHeight: '100%' }}
      >
        {/* Header bar */}
        <div
          className="hub-card-header-bar"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingBottom: '10px',
            marginBottom: '10px',
            borderBottom: '1px solid #E5E7EB',
            paddingRight: selectionNumber ? '34px' : '0px',
            transition: 'padding-right 0.15s ease',
          }}
        >
          <div className="hub-card-title-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                letterSpacing: '0.06em',
                color: '#000000',
                textTransform: 'uppercase',
              }}
            >
              {title}
            </span>
            {badge}
          </div>
          {headerAction && <div className="hub-card-header-action">{headerAction}</div>}
        </div>

        {/* Content body: HIGH CONTRAST BLACK TEXT */}
        <div
          className="flex-1 select-text"
          style={{
            fontSize: '13.5px',
            lineHeight: 1.6,
            color: '#111827',
            fontWeight: 450,
          }}
        >
          {content || children}
        </div>
      </div>
    </div>
  );
};

export default Component;
