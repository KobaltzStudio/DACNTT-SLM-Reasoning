# Preliminary independent Gold review — 63 pending D_dev problems

## Scope and source limitation

- Reviewed all 63 pending D_dev IDs in the supplied worklist.
- Joined by `problem_id` against both `gsm8k_train.jsonl` and `supplement_selected.jsonl`.
- All 63 IDs exist in both sources; statements and final answers match between the two sources.
- The supplied sources contain no full reference solution or chain-of-thought. The review therefore independently derives reasoning from the problem statement and uses the final answer and existing annotation notes only as cross-checks.
- No Gold vFinal source file is modified by this review.

## Review status

- CONFIRMED: 54
- NEEDS_USER_REVIEW: 8
- PENDING: 1

## Cases requiring user input

| Problem ID | Status | Issue / proposal |
|---|---|---|
| `gsm8k_train_00666` | NEEDS_USER_REVIEW | Gold note says ground truth 30, but both raw sources give 27 and the statement independently yields 27. Review/repair the note metadata; capability labels appear sound. |
| `gsm8k_train_00713` | PENDING | The overlap between malaria-infected and Zika-infected mosquitoes is unspecified. The supplied ground truth 15% cannot be independently derived without an unstated probability assumption or missing reference reasoning. |
| `gsm8k_train_00830` | NEEDS_USER_REVIEW | The item prices and 25% tip produce $25, but the question says 'with tax' without specifying a tax rate. The mango lassi price is explicitly $2 in the raw statement; an older Gold note incorrectly describes it as unspecified. |
| `gsm8k_train_00840` | NEEDS_USER_REVIEW | Amy's $50 is already the value of one ratio part (2:1:3). Sandra receives two parts, so multiplication and ratio suffice; division appears unnecessary. |
| `gsm8k_train_01200` | NEEDS_USER_REVIEW | The phrase '4 1/2 pound steaks' is ambiguous. Ground truth 42 supports four half-pound steaks; interpreting it as 4.5 pounds yields a different total. |
| `gsm8k_train_03048` | NEEDS_USER_REVIEW | 'Graphic novels' may be a subset of novels or a separate category. The ground truth 20% assumes three mutually exclusive categories: novels, graphic novels, comic books. |
| `gsm8k_train_06921` | NEEDS_USER_REVIEW | The final profit percentage requires profit divided by original cost. Propose adding division to the current Gold labels. |
| `gsm8k_train_07158` | NEEDS_USER_REVIEW | The apples required per pint are 20 + 40 = 60. Propose adding addition to the current Gold labels. |
| `gsm8k_train_07349` | NEEDS_USER_REVIEW | Sugar is one of three total ratio parts: 84 / (1 + 2) = 28. Multiplication is not independently required; propose removing it. |

## Full review table

| Problem ID | Original Gold | Proposed labels | Difficulty | Status | Reasoning summary |
|---|---|---|---|---|---|
| `gsm8k_train_00116` | subtraction, multiplication, division, ratio | subtraction, multiplication, division, ratio | medium | CONFIRMED | Partition the 2:5 ratio using Johnson's known five-part share; scale Mike's two parts, then subtract the $200 expense. |
| `gsm8k_train_00155` | subtraction, multiplication, fraction | subtraction, multiplication, fraction | medium | CONFIRMED | Apply one-half and one-fifth to the original 10 kg, subtract both amounts, then apply one-third to the remainder and subtract again. |
| `gsm8k_train_00166` | subtraction, multiplication, division, fraction, ratio | subtraction, multiplication, division, fraction, ratio | medium | CONFIRMED | Use the 10:45 ratio to partition 440 coins; apply the 3/4 fraction to Amalie's share and subtract the spent amount. |
| `gsm8k_train_00293` | addition, subtraction, multiplication, fraction | addition, subtraction, multiplication, fraction | medium | CONFIRMED | Each group has 8 people; multiply by 1.5 and 0.5 rolls, add consumption, then subtract from 40. |
| `gsm8k_train_00342` | multiplication, division, ratio | multiplication, division, ratio | medium | CONFIRMED | Partition 180 children into 12 ratio parts, obtain 75 boys, then divide $3,900 equally among them. |
| `gsm8k_train_00563` | addition, subtraction, multiplication, percentage | addition, subtraction, multiplication, percentage | medium | CONFIRMED | Multiply quantities by unit prices, apply the 10% discount to jackets, aggregate the bill, then apply 5% sales tax. |
| `gsm8k_train_00666` | addition, multiplication, fraction | addition, multiplication, fraction | medium | NEEDS_USER_REVIEW | Compute Anthony's 8 cats and 4 dogs; Leonel has 4 cats and 11 dogs; add 27 animals. Raw answer 27 is consistent. |
| `gsm8k_train_00678` | addition, multiplication, fraction | addition, multiplication, fraction | medium | CONFIRMED | Derive the medium and small leak rates as fractions of the larger rate; add all rates and multiply by 120 minutes. |
| `gsm8k_train_00713` | addition, subtraction, multiplication, percentage | addition, subtraction, multiplication, percentage | hard | PENDING | The required probability is a union of infection outcomes, but overlap and the exact vaccine effect assumptions are not fully specified. |
| `gsm8k_train_00724` | multiplication, division, ratio | multiplication, division, ratio | easy | CONFIRMED | Five ratio parts correspond to 45 red candles; scale the three blue parts. |
| `gsm8k_train_00779` | multiplication, division, fraction | multiplication, division, fraction | medium | CONFIRMED | Afternoon soccer campers are 3/4 of all soccer campers; invert that fraction, then invert the one-half relation to obtain all campers. |
| `gsm8k_train_00818` | subtraction, multiplication, division, fraction | subtraction, multiplication, division, fraction | medium | CONFIRMED | Spending 3/7 leaves 4/7; recover the original amount from $24, then take one-half. |
| `gsm8k_train_00830` | addition, multiplication, percentage | addition, multiplication, percentage | easy | NEEDS_USER_REVIEW | Multiply item counts by prices, add the bill, and apply the 25% tip. The statement's 'with tax' phrase does not provide a tax rate. |
| `gsm8k_train_00840` | multiplication, division, ratio | multiplication, ratio | easy | NEEDS_USER_REVIEW | Amy's $50 is one ratio part; Sandra receives two parts directly. |
| `gsm8k_train_00934` | subtraction, multiplication, division, ratio | subtraction, multiplication, division, ratio | medium | CONFIRMED | Partition 189 pets into 27 ratio parts, calculate dogs, then subtract the 10 dogs given away. |
| `gsm8k_train_01200` | addition, multiplication, fraction | addition, multiplication, fraction | medium | NEEDS_USER_REVIEW | Interpret as four half-pound steaks: 4 × 0.5 × $15 plus 1.5 × $8 = $42. Wording admits another reading. |
| `gsm8k_train_01377` | addition, multiplication, division, ratio | addition, multiplication, division, ratio | medium | CONFIRMED | Use the green paint amount to determine one ratio part, scale all three colors, then add their amounts. |
| `gsm8k_train_01384` | multiplication, percentage | multiplication, percentage | easy | CONFIRMED | Apply 80% to 40 students, then 25% to that subset. |
| `gsm8k_train_01869` | subtraction, multiplication, fraction | subtraction, multiplication, fraction | medium | CONFIRMED | Sell half, then eat 3/5 of the remainder; use subtraction to track the remaining lychees. |
| `gsm8k_train_02039` | subtraction, multiplication, percentage | subtraction, multiplication, percentage | medium | CONFIRMED | Calculate 12% commission, then save the complement of the 60% allocated to personal needs. |
| `gsm8k_train_02059` | addition, multiplication, division, percentage | addition, multiplication, division, percentage | medium | CONFIRMED | Calculate each item cost, sum the grocery total and meat total, then divide and convert to a percentage. |
| `gsm8k_train_02327` | addition, subtraction, multiplication, division, fraction | addition, subtraction, multiplication, division, fraction | hard | CONFIRMED | Derive Joshua and Miles from the half relation, derive Renz from 3/4 of Miles, combine all macarons, then divide by 2. |
| `gsm8k_train_02359` | addition, multiplication, division, fraction, ratio | addition, multiplication, division, fraction, ratio | medium | CONFIRMED | Partition 600 marbles by 3:5:7; transfer half of Brittany's share to Alex and add it to Alex's original share. |
| `gsm8k_train_02376` | multiplication, division, ratio | multiplication, division, ratio | easy | CONFIRMED | Partition 40 meters into five ratio parts and take the two-part shorter segment. |
| `gsm8k_train_02486` | addition, subtraction, multiplication, division, percentage | addition, subtraction, multiplication, division, percentage | medium | CONFIRMED | Derive scrunchies and bobby pins, total all decorations, then calculate the bobby-pin share as a percentage. |
| `gsm8k_train_02508` | multiplication, division, fraction, ratio | multiplication, division, fraction, ratio | medium | CONFIRMED | Apply 3/4 to 400 tickets, then partition the transferred tickets by 4:11 and select Finley's 11 parts. |
| `gsm8k_train_02634` | multiplication, division, ratio | multiplication, division, ratio | easy | CONFIRMED | Use Chloe's 24 wins to determine one ratio part and scale Max's three parts. |
| `gsm8k_train_02713` | subtraction, multiplication, division, ratio | subtraction, multiplication, division, ratio | medium | CONFIRMED | Partition 126 years by 4:3:7, calculate the first two ages and subtract. |
| `gsm8k_train_02837` | addition, multiplication, fraction | addition, multiplication, fraction | medium | CONFIRMED | Apply one-half to Jack's circumference, add 9 for Charlie, then apply 2/3 to Charlie for Bill. |
| `gsm8k_train_02871` | subtraction, multiplication, division, percentage | subtraction, multiplication, division, percentage | hard | CONFIRMED | Apply the 25% property-value increase, invert the 2% tax constraint to find maximum taxable value, then subtract the post-rail value. |
| `gsm8k_train_02893` | multiplication, fraction | multiplication, fraction | easy | CONFIRMED | Apply one-third to 42, then one-half to the resulting application count. |
| `gsm8k_train_02960` | addition, subtraction, multiplication, division, fraction | addition, subtraction, multiplication, division, fraction | hard | CONFIRMED | Set the two spending expressions equal to the starting amount and solve the resulting linear equation. |
| `gsm8k_train_03048` | subtraction, multiplication, division, percentage | subtraction, multiplication, division, percentage | medium | NEEDS_USER_REVIEW | Calculate 65% of 120, subtract novels and graphic novels under the intended disjoint-category interpretation, then calculate the remaining percentage. |
| `gsm8k_train_03116` | subtraction, multiplication, percentage | subtraction, multiplication, percentage | medium | CONFIRMED | Each year 80% remains; multiply the retention rate across two years. |
| `gsm8k_train_03289` | subtraction, multiplication, fraction | subtraction, multiplication, fraction | medium | CONFIRMED | Apply each fraction to the current remainder in sequence, subtracting after each day's consumption. |
| `gsm8k_train_03316` | subtraction, multiplication, fraction | subtraction, multiplication, fraction | medium | CONFIRMED | Apply 2/5, then one-half, then 3/4 to successive remainders. |
| `gsm8k_train_03355` | addition, subtraction, multiplication, division, percentage | addition, subtraction, multiplication, division, percentage | medium | CONFIRMED | Calculate initial wins, add wins from the second batch, update total games, and divide to obtain the new percentage. |
| `gsm8k_train_03360` | subtraction, multiplication, percentage | subtraction, multiplication, percentage | medium | CONFIRMED | Subtract pages written, apply 30% to the remainder, then subtract the 20% damaged portion of the still-empty pages. |
| `gsm8k_train_03439` | subtraction, multiplication, percentage | subtraction, multiplication, percentage | medium | CONFIRMED | 20% of ads are unblocked; 80% of that subset are uninterested, giving 16% of all ads. |
| `gsm8k_train_03734` | addition, subtraction, multiplication, fraction | addition, subtraction, multiplication, fraction | medium | CONFIRMED | Calculate authentic purses and handbags using complementary fractions, then add the two authentic counts. |
| `gsm8k_train_03879` | subtraction, multiplication, fraction | subtraction, multiplication, fraction | medium | CONFIRMED | Derive women, men and children; subtract those who leave and combine the remaining groups. |
| `gsm8k_train_03882` | subtraction, multiplication, fraction | subtraction, multiplication, fraction | medium | CONFIRMED | Subtract confiscated firecrackers, remove the defective fraction, then take half of the good remainder. |
| `gsm8k_train_03999` | subtraction, multiplication, percentage | subtraction, multiplication, percentage | easy | CONFIRMED | Subtract the Chinese and US percentages from 100%; the remainder corresponds to Japanese stamps. |
| `gsm8k_train_04046` | subtraction, multiplication, division, ratio | subtraction, multiplication, division, ratio | medium | CONFIRMED | Partition 78 slices by 5:8, calculate the waiter's share, then subtract 20. |
| `gsm8k_train_04231` | subtraction, multiplication, percentage | subtraction, multiplication, percentage | medium | CONFIRMED | Calculate tax before and after the changes, then subtract the old tax from the new tax. |
| `gsm8k_train_04470` | multiplication, division, ratio | multiplication, division, ratio | medium | CONFIRMED | Use the shortest 2-part segment to determine one ratio part and scale the total 12 parts. |
| `gsm8k_train_05030` | subtraction, multiplication, division, percentage | subtraction, multiplication, division, percentage | hard | CONFIRMED | Calculate male/female counts and male votes, determine the minimum winning vote count, then solve the required female-vote percentage. |
| `gsm8k_train_05287` | subtraction, multiplication, percentage | subtraction, multiplication, percentage | medium | CONFIRMED | Calculate the first two response groups, apply 80% to the remaining respondents, then identify the residual group. |
| `gsm8k_train_05356` | addition, multiplication, division, ratio | addition, multiplication, division, ratio | easy | CONFIRMED | Use Parker's two parts to determine one part, then scale to all five ratio parts. |
| `gsm8k_train_05451` | subtraction, multiplication, division, ratio | subtraction, multiplication, division, ratio | medium | CONFIRMED | Subtract yellow marbles, partition the remainder by 3:4, then subtract yellow count from red count. |
| `gsm8k_train_05463` | multiplication, division, ratio | multiplication, division, ratio | easy | CONFIRMED | Use 44 gallons as four ratio parts and scale to seven distance parts. |
| `gsm8k_train_05486` | subtraction, multiplication, division, ratio | subtraction, multiplication, division, ratio | medium | CONFIRMED | Partition 100 students into five ratio parts and subtract girls from boys. |
| `gsm8k_train_05565` | multiplication, division, ratio | multiplication, division, ratio | easy | CONFIRMED | Partition 555 cattle into 37 ratio parts and scale the 27 bull parts. |
| `gsm8k_train_05585` | multiplication, division, ratio | multiplication, division, ratio | easy | CONFIRMED | Partition 260 students into 13 ratio parts and select the eight girl parts. |
| `gsm8k_train_06274` | multiplication, division, ratio | multiplication, division, ratio | easy | CONFIRMED | Partition 400 stationery items into ten ratio parts and select seven book parts. |
| `gsm8k_train_06506` | subtraction, multiplication, division, ratio | subtraction, multiplication, division, ratio | medium | CONFIRMED | Partition 36 marbles into nine ratio parts, calculate Manny's share, then subtract the two given away. |
| `gsm8k_train_06921` | subtraction, multiplication, percentage | subtraction, multiplication, division, percentage | medium | NEEDS_USER_REVIEW | Apply markup and discount percentages, calculate profit, then divide profit by cost to obtain profit percentage. |
| `gsm8k_train_07080` | subtraction, multiplication, division, ratio | subtraction, multiplication, division, ratio | medium | CONFIRMED | Partition 65 items by 4:9, multiply counts by prices and subtract the two expenditures. |
| `gsm8k_train_07117` | subtraction, multiplication, percentage | subtraction, multiplication, percentage | easy | CONFIRMED | Calculate 25% of the 40% trip mornings, then take the complement. |
| `gsm8k_train_07158` | multiplication, division, ratio | addition, multiplication, division, ratio | hard | NEEDS_USER_REVIEW | Calculate total apples picked, determine apples needed per pint from 20 + 40, then divide total apples by 60. |
| `gsm8k_train_07349` | multiplication, division, ratio | division, ratio | easy | NEEDS_USER_REVIEW | The 84 cups represent three total ratio parts; one part, the sugar quantity, is 28 cups. |
| `gsm8k_train_00239` | addition, subtraction, percentage | addition, subtraction, percentage | medium | CONFIRMED | Use inclusion-exclusion: 50% + 25% - 5% overlap = 70% killed; 30% remain. |
| `gsm8k_train_00942` | subtraction, multiplication, fraction | subtraction, multiplication, fraction | easy | CONFIRMED | Calculate one-fifth of 200, double that number for the second event, then subtract both blown-up groups from 200. |

## Important interpretation rules applied

- A fraction of a quantity does not automatically add `division`; `division` is included when an independent sharing/grouping/unit-value/inverse operation is required.
- `ratio` is included only where proportional partitioning or scaling is central.
- Extractor predictions are not treated as evidence that Gold is wrong.
- `NEEDS_USER_REVIEW` and `PENDING` records must not be promoted to confirmed without resolving the stated issue.
- This is a preliminary adjudication proposal, not a frozen Gold release.
