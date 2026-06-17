with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

out_lines = []
for idx in range(1640, min(1750, len(lines))):
    out_lines.append(f"{idx+1}: {lines[idx]}")

with open("scratch/inspected_lines.txt", "w", encoding="utf-8") as out:
    out.writelines(out_lines)

print("Wrote lines to scratch/inspected_lines.txt")
