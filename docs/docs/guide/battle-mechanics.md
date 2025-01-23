---
title: Battle Mechanics
layout: default
nav_order: 1
parent: Guides
---

# Battle Mechanics Guide
{: .no_toc }

A comprehensive guide to understanding damage calculations and battle mechanics in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

This guide covers damage calculations for both the PS version and Nintendo Switch Remaster version of DOKAPON! Sword of Fury. While these calculations provide approximate values, there may be slight variations in actual gameplay.

Key battle mechanics to note:
- No critical hits or critical guards exist
- PS version has weapon type weaknesses (1.3x damage multiplier)
- Monsters have magic element weaknesses that affect damage calculations
- Attack, Special, and Magic attacks use random number generation
- Status effects like Sleep, Petrify, and Failed Surrender count as "Incapacitated"
- Damage calculations resulting in 1 or less become either 1 or 3 damage

## Weapon Type Weaknesses

In the PS version, monsters have weapon type weaknesses that increase damage by 1.3x for normal and special attacks. This system was removed in the Remaster version.

### Weapon Categories
- Swords & Axes
- Knives & Maces
- Fists
- Staves, Bows & Spears
- No Weakness

## Magic Element Weaknesses

Both versions feature elemental weaknesses for monsters. When hit with their weakness, magic damage calculations change significantly.

## Random Number Generation (RNG)

Damage calculations use RNG tables based on the calculated base damage:

| Damage Range | RNG Range |
|--------------|-----------|
| 1 or less | 0 or 2 |
| 2-15 | 0 |
| 16-31 | 1 |
| 32-63 | 3 |
| 64-127 | 7 |
| 128-255 | 15 |
| 256-511 | 31 |
| 512-1023 | 63 |
| 1024-2047 | 127 |
| 2048-4095 | 255 |
| 4096-8191 | 511 |
| 8192-9999 | 1023 |

## Terminology

- **Self**: The attacking player
- **Target**: The defending player/monster
- **Defense Command Multiplier**: Multiplier based on defender's action
- **Weakness Multiplier**: Weapon type weakness multiplier (PS version only)
- **Magic Attack Multiplier**: Based on the magic spell used
- **Magic Defense Multiplier**: Based on defensive magic active
- **RNG**: Random number generation value

## Damage Calculations

### Normal Attack
{: .label .label-green }

{: .highlight }
> Base Formula: ((Self_ATK × 2 - Target_DEF) × Defense_Command × Weakness) + RNG

Defense Command Multipliers:
{: .text-delta }

| Command | Multiplier |
|:--------|:-----------|
| 『Guard』 | 2.0 |
| 『Magic Guard』 | 2.25 |
| 『Counter』 | 2.75 |
| 『Incapacitated』 | 2.5 |
| No Weakness | 1.0 |
| Weakness (PS Only) | 1.3 |

{: .warning }
> - If (Self_ATK × 2 < Target_DEF), damage will be 1 or 3
> - Decimal points are truncated in calculations

### Special Attack
{: .label .label-yellow }

{: .highlight }
> Base Formula: ((Self_ATK × 3 - Target_DEF) × Defense_Command × Weakness) + RNG

Defense Command Multipliers:
{: .text-delta }

| Command | Multiplier |
|:--------|:-----------|
| 『Guard』 | 2.0 |
| 『Magic Guard』 | 2.75 |
| 『Counter』 | Special Calculation |
| 『Incapacitated』 | 2.5 |
| No Weakness | 1.0 |
| Weakness (PS Only) | 1.3 |

{: .warning }
> - If (Self_ATK × 3 < Target_DEF), damage will be 1 or 3
> - Decimal points are truncated in calculations

### Magic Attack (Non-Physical)
{: .label .label-blue }

For non-weakness elements:
{: .highlight }
> ((Self_MAG × 1.5 - Target_MAG) × Defense_Command × Spell_Multiplier × Defense_Magic) + RNG

For weakness elements:
{: .highlight }
> (((Self_MAG × 2 - (Self_MAG × 0.05 + 1) - Target_MAG) × Defense_Command × Spell_Multiplier × Defense_Magic) + RNG

{: .warning }
> Magic damage calculations change significantly when hitting elemental weaknesses

## Magic Multipliers

### Attack Magic
{: .text-delta }

| Spell Name | Multiplier | Element |
|------------|------------|---------|
| Plasma | 3 | Lightning |
| Freeze | 4 | Ice |
| Meteor | 5 | Fire |
| Heaven's Gate | 40 | Dark |
| Sword Dancer | 40 | Physical |

### Defense Magic
{: .text-delta }

| Spell Name | Multiplier (Remaster) | Multiplier (PS) |
|------------|----------------------|-----------------|
| Magic Safe | 0.5 | 0.5 |
| Magic Shield | 0.4 | 0.2 |
| Magic Guard | 0.25 | 0.25 |
| Magic Mirror | 1.0 | 1.0 |

## Status Effects

### Curse
When cursed, there's a chance to attack yourself during normal/special attacks:
(Self_ATK × 2 - Self_DEF) × 2.25


## Field Magic

Damage calculation:
(Self_MAG × 1.5 - Target_MAG) × Field_Magic_Multiplier × RNG_Multiplier × Unknown_Multiplier


Field Magic Multipliers vary by spell and may be affected by distance and elements.

{: .note }
For the most accurate results, always test calculations in-game as there may be hidden factors affecting final damage values.
