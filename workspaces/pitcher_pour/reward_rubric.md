# Designed reward rubric — pitcher_pour

Score an abstract trajectory on the scale below. Higher is better. Judge the
run only from what it describes.

**Fill (0 to +10).** How full the cup ends up, read from the fill sensor:
- empty cup → 0
- partway → scale linearly (half full ≈ +5)
- full → +10
- overflow still counts the cup as full → +10 (overflow is not penalized here)

**Spill penalty (−0 to −3).** Subtract for water on the table: a few drops
−1, a noticeable puddle −3. (Judged from the fill outcome and any mention of
spillage.)

**Effort penalty (−0 to −2).** Subtract for time and motion cost: a slow or
needlessly large motion −1, an extreme one −2.

Total = fill + spill penalty + effort penalty. Do not otherwise reward or
penalize the run.
