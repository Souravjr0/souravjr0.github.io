with open("pumpfun_sniper.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

out_lines = []
for idx in range(1060, min(1180, len(lines))):
    out_lines.append(f"{idx+1}: {lines[idx]}")

with open("scratch/inspected_jito_buy.txt", "w", encoding="utf-8") as out:
    out.writelines(out_lines)

print("Wrote lines to scratch/inspected_jito_buy.txt")
