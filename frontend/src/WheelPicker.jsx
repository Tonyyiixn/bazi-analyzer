import { useLayoutEffect, useRef } from 'react';

// A scrollable, snap-to-center "wheel" selector - iOS-style date picker
// column. Scroll (or click an item) to change the value; the item centered
// in the highlight band is the selected one.
export default function WheelPicker({
  options, value, onChange, label, formatOption,
  itemHeight = 36, visibleItems = 5, fontSize = 'text-base',
}) {
  const ITEM_HEIGHT = itemHeight;
  const WHEEL_HEIGHT = ITEM_HEIGHT * visibleItems;
  const PADDING = (WHEEL_HEIGHT - ITEM_HEIGHT) / 2;

  const containerRef = useRef(null);
  const scrollTimeout = useRef(null);
  const suppressNextScroll = useRef(false);

  // Keep the wheel in sync when `value` changes from outside this component
  // (e.g. the Day wheel gets clamped after Month/Year changes).
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const index = options.indexOf(value);
    if (index === -1) return;
    const target = index * ITEM_HEIGHT;
    if (Math.abs(el.scrollTop - target) > 1) {
      suppressNextScroll.current = true;
      el.scrollTop = target;
    }
  }, [value, options, ITEM_HEIGHT]);

  const handleScroll = () => {
    if (suppressNextScroll.current) {
      suppressNextScroll.current = false;
      return;
    }
    clearTimeout(scrollTimeout.current);
    scrollTimeout.current = setTimeout(() => {
      const el = containerRef.current;
      if (!el) return;
      const index = Math.round(el.scrollTop / ITEM_HEIGHT);
      const clamped = Math.min(Math.max(index, 0), options.length - 1);
      el.scrollTo({ top: clamped * ITEM_HEIGHT, behavior: 'smooth' });
      const newValue = options[clamped];
      if (newValue !== value) onChange(newValue);
    }, 100);
  };

  const scrollToIndex = (index) => {
    containerRef.current?.scrollTo({ top: index * ITEM_HEIGHT, behavior: 'smooth' });
  };

  return (
    <div className="flex flex-col items-center">
      {label && <label className="block text-sm font-medium text-parchment-400 mb-1">{label}</label>}
      <div className="relative w-full">
        {/* Selection highlight band */}
        <div
          className="pointer-events-none absolute left-0 right-0 border-y border-gold-500/50 bg-gold-500/5 z-10"
          style={{ top: PADDING, height: ITEM_HEIGHT }}
        />
        {/* Fade edges */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-3 bg-gradient-to-b from-ink-950 to-transparent z-10" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-3 bg-gradient-to-t from-ink-950 to-transparent z-10" />

        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="overflow-y-auto no-scrollbar bg-ink-950 border border-ink-700 rounded"
          style={{ height: WHEEL_HEIGHT, scrollSnapType: 'y mandatory' }}
        >
          <div style={{ height: PADDING }} />
          {options.map((opt, i) => (
            <div
              key={opt}
              onClick={() => scrollToIndex(i)}
              className={`flex items-center justify-center cursor-pointer select-none transition-colors ${fontSize} ${
                opt === value ? 'text-gold-400 font-semibold' : 'text-parchment-600 hover:text-parchment-400'
              }`}
              style={{ height: ITEM_HEIGHT, scrollSnapAlign: 'center' }}
            >
              {formatOption ? formatOption(opt) : opt}
            </div>
          ))}
          <div style={{ height: PADDING }} />
        </div>
      </div>
    </div>
  );
}
