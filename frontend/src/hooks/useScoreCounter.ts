import { useEffect, useState } from 'react'

export function useScoreCounter(target: number, duration = 1200): number {
  const [current, setCurrent] = useState(0)

  useEffect(() => {
    if (target === 0) return
    const start = performance.now()
    let raf: number

    const tick = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      // easeOut cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setCurrent(Math.round(target * eased * 100))
      if (progress < 1) raf = requestAnimationFrame(tick)
    }

    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])

  return current
}
