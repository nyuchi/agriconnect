# Example: a farmer in Gweru asks when to plant maize

Refs #2. Values below were read from the live databases on 2026-11-01. Every statement is marked:
**[observed]** read from a source as stored, **[derived]** computed from stored values,
**[unverified]** not yet backed by data we hold.

> Farmer (Shamwari, Shona or English): "Ndipedzise rini kudyara chibage kuGweru?" /
> "When should I plant maize near Gweru?"

## 1. Place to region and province

`places.placeKnowledge` has a Gweru entry (id `019f07ed-b519-70c4-8324-2d24aa650531`) at
longitude 29.82003, latitude -19.45004 **[observed]**.

| Answer | Value | Marking |
| --- | --- | --- |
| Province | Midlands, `ZW-MI`, P-code `ZW17` (the entry's calendar reference region is "Midlands") | [observed], join per `docs/place-to-region.md` |
| Natural Region, 1960 | **not available**: no polygon is loaded | [unverified] |
| Natural Region, 2020 | **not available** | [unverified] |
| District | **not available**: no district boundaries held | [unverified] |

Shamwari must say so rather than guess "Region 3". The stored rainfall (below) is a hint, not a
classification.

## 2. Province crop calendar

From `placeKnowledge.agriculture.crops` for Gweru, source GEOGLAM Crop Monitor Sub-National Crop
Calendars (CM4EW) v1.3, CC-BY-4.0, doi:10.5281/zenodo.15850408 (Becker-Reshef, Barker et al.):

| Maize stage | Day of year stored | Calendar date (non-leap year) | Marking |
| --- | --- | --- | --- |
| planting | 320 | 16 November | [observed], then converted by hand [derived] |
| vegetative | 350 | 16 December | same |
| harvest | 60 | 1 March | same |
| end of season | 152 | 1 June | same |

The values are the regional (Midlands) calendar, not specific to Gweru's soils or Natural Region.
How GEOGLAM defines each stage boundary was not read here; Shamwari should not describe the
stages beyond their names.

## 3. Rainfall

- Long-term, from the entry's `climate.normals` (ERA5 1991-2020 via Open-Meteo, CC-BY-4.0, modelled
  [observed as stored]): November 94.3 mm, December 182.5 mm, January 158 mm, February 113.2 mm,
  March 80.2 mm. The stored monthly values add to about 700 mm a year **[derived]**. Rainy months
  (60 mm or more): 11, 12, 1, 2, 3 **[derived, as stored in `agriculture.derived`]**.
- This season: `agriculture.rainfallDekadal` for `ZW17` (CHIRPS via WFP, CC-BY-4.0, 10-day
  totals, `f` final / `p` preliminary). The latest rows are preliminary. **Not quoted here** because
  I did not read the Midlands document; Shamwari reads the latest dekads and labels preliminary ones.

## 4. What Shamwari can say

> "Near Gweru, in Midlands province, the usual maize planting window starts in mid-November
> (about 16 November), when the main rains are building. The long-term average rainfall in
> November is about 94 mm, rising to about 180 mm in December. [Source: GEOGLAM crop calendar for
> Midlands, v1.3; ERA5 normals 1991-2020.] I do not yet have the Natural Region for your exact
> location, so I cannot tell you whether your area is drier or wetter than the Midlands average.
> This season's 10-day rainfall is read from CHIRPS and the latest figure is preliminary."

Every sentence maps to a row above. Shamwari must **not** add "plant when the rains are established" or any trigger rule: that is agronomic advice with no source here **[unverified]** (item 3 below).

## 5. What is missing for a full answer

1. Natural Region polygons (owner decision, `docs/natural-regions.md`).
2. District boundaries in `places` (owner decision, `docs/place-to-region.md`).
3. A rule for combining region and rainfall into a recommendation. That is agronomy; it needs a
   named agronomic source (for example AGRITEX guidance) and is **not** derived here.
