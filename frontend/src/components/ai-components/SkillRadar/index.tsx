import { motion } from "framer-motion";
import styles from "./SkillRadar.module.css";

interface Axis { label: string; score: number; }
interface Props { data: { axes: Axis[]; summary: string } }

const SIZE = 220;
const CENTER = SIZE / 2;
const RADIUS = 80;
const LEVELS = 4;

function polarToXY(angle: number, r: number) {
  const rad = (angle - 90) * (Math.PI / 180);
  return { x: CENTER + r * Math.cos(rad), y: CENTER + r * Math.sin(rad) };
}

export function SkillRadar({ data }: Props) {
  const { axes = [], summary } = data;
  if (axes.length < 3) return null;

  const n = axes.length;
  const step = 360 / n;

  const polygonPoints = axes
    .map((ax, i) => {
      const { x, y } = polarToXY(i * step, (ax.score / 100) * RADIUS);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className={styles.container}>
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
        {/* Grid rings */}
        {Array.from({ length: LEVELS }).map((_, li) => {
          const r = (RADIUS / LEVELS) * (li + 1);
          const pts = axes.map((_, i) => {
            const { x, y } = polarToXY(i * step, r);
            return `${x},${y}`;
          }).join(" ");
          return <polygon key={li} points={pts} fill="none" stroke="var(--color-border)" strokeWidth="1" />;
        })}

        {/* Axis lines */}
        {axes.map((_, i) => {
          const outer = polarToXY(i * step, RADIUS);
          return <line key={i} x1={CENTER} y1={CENTER} x2={outer.x} y2={outer.y} stroke="var(--color-border)" strokeWidth="1" />;
        })}

        {/* Data polygon */}
        <motion.polygon
          points={polygonPoints}
          fill="var(--color-accent-muted)"
          stroke="var(--color-accent)"
          strokeWidth="2"
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{ transformOrigin: `${CENTER}px ${CENTER}px` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />

        {/* Axis labels */}
        {axes.map((ax, i) => {
          const pos = polarToXY(i * step, RADIUS + 18);
          return (
            <text
              key={i}
              x={pos.x}
              y={pos.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="11"
              fill="var(--color-fg-muted)"
              fontFamily="var(--font-sans)"
            >
              {ax.label}
            </text>
          );
        })}

        {/* Score dots */}
        {axes.map((ax, i) => {
          const { x, y } = polarToXY(i * step, (ax.score / 100) * RADIUS);
          return <circle key={i} cx={x} cy={y} r="3" fill="var(--color-accent)" />;
        })}
      </svg>

      {/* Scores legend */}
      <div className={styles.scores}>
        {axes.map((ax) => (
          <div key={ax.label} className={styles.scoreRow}>
            <span className={styles.scoreLabel}>{ax.label}</span>
            <div className={styles.scoreBar}>
              <motion.div
                className={styles.scoreBarFill}
                initial={{ width: 0 }}
                animate={{ width: `${ax.score}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
            <span className={styles.scoreValue}>{ax.score}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
