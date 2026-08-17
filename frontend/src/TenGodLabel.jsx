import { useEffect, useRef, useState } from 'react';
import { TEN_GOD_INFO } from './tenGodInfo';

// Wraps a Ten God name (e.g. "Direct Officer") with a short explanatory
// tooltip - hover to reveal on desktop, tap to toggle on mobile (no real
// hover there). Falls back to plain text for non-Ten-God values like "Day
// Master"/"N/A"/"Unknown" that sometimes show up in the same slot.
export default function TenGodLabel({ name, className = '' }) {
  const info = TEN_GOD_INFO[name];
  // Separate hover/click state so a click doesn't fight with hover: without
  // this, hovering opens the tooltip, then a click on the same element
  // toggles that single boolean straight back to closed (Playwright's
  // .click() - and a real trackpad user's click-to-pin - both hover before
  // they click). `clicked` pins the tooltip open independent of the mouse
  // leaving, until clicked again or something else is clicked.
  const [hovered, setHovered] = useState(false);
  const [clicked, setClicked] = useState(false);
  const open = hovered || clicked;
  const ref = useRef(null);

  useEffect(() => {
    if (!clicked) return;
    const handleOutsideClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setClicked(false);
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [clicked]);

  if (!info) return <span className={className}>{name}</span>;

  return (
    <span
      ref={ref}
      className="relative inline-block"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setClicked((v) => !v); }}
        className={`${className} bg-transparent border-none p-0 m-0 font-inherit inline underline decoration-dotted decoration-1 underline-offset-2 cursor-help`}
        aria-expanded={open}
      >
        {name}
      </button>
      {open && (
        <div className="absolute z-50 left-1/2 -translate-x-1/2 top-full mt-1 w-56 bg-ink-950 border border-ink-700 rounded p-2 shadow-lg text-left normal-case">
          <p className="text-xs font-semibold text-parchment-200">
            {name} <span className="text-parchment-600 font-normal">({info.chinese})</span>
          </p>
          <p className="text-[11px] text-parchment-400 mt-1 leading-snug">{info.blurb}</p>
        </div>
      )}
    </span>
  );
}
