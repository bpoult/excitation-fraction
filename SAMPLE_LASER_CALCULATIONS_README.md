# SAMPLE & LASER CALCULATIONS — Spreadsheet Reference

## Overview

This spreadsheet has two tabs. Together they answer two experimental design questions for ultrafast transient absorption spectroscopy on a liquid microjet:

1. **Tab 1 (SAMPLE CONCENTRATION):** Given a target absorbance at the excitation wavelength, what concentration of sample is needed, and how much material (by mass) must be dissolved in the reservoir?
2. **Tab 2 (LASER FLUENCE - 400 nm):** Given that absorbance and a target average excitation fraction `<fexc>`, what laser pulse energy, power, and fluence are required?

The sample is [Co(bpy)₃][Cl]₃ dissolved in an ACN:DMSO solvent mixture, excited at 393 nm. The laser beam passes through a cylindrical liquid jet of known diameter.

---

## Tab 1 — SAMPLE CONCENTRATION

### User Inputs

| Cell | Label | Value | Units | Notes |
|------|-------|-------|-------|-------|
| `B2` | Jet diameter | 5 | µm | Diameter of the liquid microjet; this is the optical path length through the sample |
| `B3` | Reservoir volume | 35 | mL | Total volume of sample solution in the reservoir |
| `B4` | Laser absorbance in jet | 0.025 | — | Target optical density (OD) of the sample at the excitation wavelength |
| `H2` | Sample name | [Co(bpy)₃][Cl]₃ | — | |
| `I2` | Extinction coefficient @ 393 nm | 123 | M⁻¹cm⁻¹ | Molar extinction coefficient of the sample at the excitation wavelength |
| `J2` | ACN:DMSO solvent ratio | 306 | — | Volumetric ratio of acetonitrile to DMSO |
| `L2` | Molecular weight | 633.698 | g/mol | Molecular weight of [Co(bpy)₃][Cl]₃ |

### Background Physics — Beer-Lambert Law

The Beer-Lambert Law describes how light is attenuated as it passes through an absorbing solution:

$$A = \varepsilon \cdot c \cdot l$$

where:
- **A** is the absorbance (dimensionless, also called optical density or OD)
- **ε** is the molar extinction coefficient (M⁻¹cm⁻¹)
- **c** is the molar concentration of the absorbing species (M = mol/L)
- **l** is the path length through the sample (cm)

Given a target absorbance A, a known ε, and a known path length l (the jet diameter), we can rearrange to solve for the required concentration:

$$c = \frac{A}{\varepsilon \cdot l}$$

Once the concentration is known, the total mass of solute needed is:

$$m \, (\text{g}) = c \, (\text{mol/L}) \times V \, (\text{L}) \times M_W \, (\text{g/mol})$$

### Calculated Cells

| Cell | Label | Formula | Derivation |
|------|-------|---------|------------|
| `B5` | Laser transmission in jet | `=10^-B4` | From Beer-Lambert: transmittance T = 10^(−A). Fraction of laser light that passes through the jet without being absorbed. |
| `C11` | Sample concentration (mM) | `=($B$4/(I2*$B$2*0.0001))*1000` | Rearranged Beer-Lambert: c(M) = A / (ε · l). B2 is in µm, converted to cm by multiplying by 0.0001 (1 µm = 10⁻⁴ cm). Result multiplied by 1000 to convert M → mM. |
| `E11` | Weight per reservoir volume (mg) | `=(C11/1000)*($B$3/1000)*L2*1000` | mass = c(mM)/1000 × V(mL)/1000 × MW(g/mol) × 1000 mg/g. Converts concentration to mol/L, volume to L, and final mass to mg. |

---

## Tab 2 — LASER FLUENCE - 400 nm

### User Inputs

| Cell | Label | Value | Units | Notes |
|------|-------|-------|-------|-------|
| `B2` | Sample absorbance | 0.025 | — | Manually copied from Tab 1 `B4`. **Not a live cell reference** — must be updated by hand if Tab 1 changes. |
| `B4` | Laser wavelength | 393 | nm | Central wavelength of the excitation pulse |
| `B5` | Laser spot size (vertical) | 240 | µm FWHM | Vertical 1/e² beam radius at the sample |
| `B6` | Laser spot size (horizontal) | 100 | µm FWHM | Horizontal 1/e² beam radius at the sample |
| `B7` | Laser repetition rate | 33,000 | Hz | Pulse repetition rate of the laser |
| `B12` | Requested `<fexc>` | 0.24 | — | Target **average** excitation fraction across the jet depth |
| `G2` | Sample name | [Co(bpy)₃][Cl]₃ | — | |
| `H2` | Extinction coefficient @ 393 nm | 123 | M⁻¹cm⁻¹ | **Correct value is 123** (the original spreadsheet contained a typo of 124). Must match Tab 1 `I2`. |

### Background Physics — Excitation Fraction

The **excitation fraction** `fexc` is the probability that a given molecule in the sample absorbs a photon during a single laser pulse. In the linear (low-fluence) regime:

$$f_{exc} = \sigma \cdot \Phi$$

where:
- **σ** is the absorption cross section of the molecule (cm²)
- **Φ** is the photon fluence of the pulse (photons/cm²) = (pulse energy in J) / (beam area in cm²) / (energy per photon in J)

Because the laser beam is attenuated as it travels through the absorbing jet, the fluence — and therefore `fexc` — is not uniform across the jet depth. Molecules near the **front face** of the jet see higher fluence than molecules near the **back face**. The attenuation follows Beer-Lambert:

$$\Phi(z) = \Phi_0 \cdot 10^{-\varepsilon c z}$$

The spreadsheet handles this by computing:
- **fexc at the front face:** The front face of the jet has been attenuated by only half the jet's OD (A/2) before the beam enters. Relative to the midpoint reference fluence, the front face sees `10^(+A/2)` times higher fluence. So: `fexc_front = <fexc> / 10^(−A/2)`
- **fexc at the back face:** The back face sees the beam after it has been attenuated by the full OD of the jet: `fexc_back = fexc_front × 10^(−A)`

The **requested `<fexc>`** (cell `B12`) is the target spatially-averaged excitation fraction. The pulse energy is solved for by rearranging `<fexc> = σ · Φ_effective`, where `Φ_effective` accounts for the beam attenuation at the midpoint of the jet (factor of `10^(−A/2)`).

### Background Physics — Absorption Cross Section

The absorption cross section σ (cm²) is related to the molar extinction coefficient ε (M⁻¹cm⁻¹) by:

$$\sigma \, (\text{cm}^2) = \varepsilon \, (\text{M}^{-1}\text{cm}^{-1}) \times \frac{1000 \cdot \ln(10)}{N_A}$$

where N_A = 6.022 × 10²³ mol⁻¹ is Avogadro's number. The factor of 1000 converts from per-liter to per-cm³ (1 L = 1000 cm³). Numerically:

$$\frac{1000 \cdot \ln(10)}{6.022 \times 10^{23}} \approx 3.82 \times 10^{-21}$$

This is the hardcoded factor used in cell `I2`: `σ = 3.82×10⁻²¹ × ε`.

### Intermediate Constants (Calculated)

| Cell | Label | Formula | Derivation |
|------|-------|---------|------------|
| `L2` | Energy per photon, hc/λ | `=(6.62607015E-34 * 299792458) / (B4 * 1e-9)` | Planck's relation E = hc/λ. h = 6.626×10⁻³⁴ J·s, c = 2.998×10⁸ m/s, λ converted from nm to m. Result in Joules/photon. |
| `L3` | Laser beam area | `=PI()*(B5/2)*(B6/2)*1e-8` | Area of an ellipse: π·a·b where a and b are the semi-axes. B5 and B6 are full diameters in µm; divided by 2 to get radii. Each radius converted from µm to cm by ×10⁻⁴, so the product of two radii is scaled by ×10⁻⁸. Result in cm². |
| `I2` | Absorption cross section | `=(3.82E-21)*H2` | σ(cm²) = ε × 1000·ln(10)/Nₐ — see derivation above. Result in cm²/molecule. |

### Output Calculated Cells (Row 14, sample: [Co(bpy)₃]³⁺)

| Cell | Label | Formula | Derivation |
|------|-------|---------|------------|
| `C14` | Pulse energy (µJ) | `=($L$2*$B$12*$L$3*1e6) / ((10^(-$B$2/2))*I2)` | Rearranging `<fexc> = σ·Φ_mid` for pulse energy: E = `<fexc>` · (hc/λ) · Area / (σ · 10^(−A/2)). The `10^(−A/2)` factor accounts for beam attenuation at the jet midpoint. Multiplied by 10⁶ to return µJ. |
| `D14` | Avg. power (mW) | `=(C14*1e-6)*$B$7*1000` | Power (W) = pulse energy (J) × rep rate (Hz). C14 converted from µJ to J (×10⁻⁶), then multiplied by rep rate and ×1000 for mW. |
| `E14` | Avg. power (µW) | `=D14*1000` | D14 × 1000. Unit conversion only. |
| `F14` | Fluence (mJ/cm²) | `=(C14/1000)/$L$3` | Fluence = pulse energy / beam area. C14 in µJ divided by 1000 → mJ, divided by L3 (cm²). |
| `G14` | N(photons) per pulse | `=C14/1e6/$L$2` | N = E(J) / (hc/λ). C14 converted from µJ to J (÷10⁶), divided by energy per photon L2. |
| `H14` | fexc at jet front face | `=$B$12/(10^(-$B$2/2))` | Front face sees higher fluence than the midpoint. Corrects `<fexc>` by the Beer-Lambert factor for the first half of the jet: fexc_front = `<fexc>` / 10^(−A/2). |
| `I14` | fexc at jet back face | `=$H$14*(10^(-$B$2))` | Back face fluence is attenuated by the full OD of the jet relative to the front face: fexc_back = fexc_front × 10^(−A). |
| `J14` | Peak intensity (W/cm²) | `=(C14/1000)/$L$3/(5e-14)` | Intensity = Fluence (J/cm²) / pulse duration. Pulse duration is assumed to be **50 fs = 5×10⁻¹⁴ s** (hardcoded, not an exposed input). |

---

## Notes and Known Issues

1. **Absorbance duplication between tabs:** Tab 2 cell `B2` (sample absorbance) is intentionally a **manual copy** of Tab 1 cell `B4`. It is not a live Excel cell reference. If the target absorbance is changed in Tab 1, Tab 2 `B2` must be updated by hand.

2. **Extinction coefficient typo:** The original spreadsheet had Tab 2 `H2` = 124 M⁻¹cm⁻¹. The **correct value is 123 M⁻¹cm⁻¹**, consistent with Tab 1 `I2`. The README reflects the corrected value. Update `H2` in the spreadsheet accordingly.

3. **Pulse duration assumption:** The peak intensity calculation in `J14` assumes a **50 fs pulse duration** (5×10⁻¹⁴ s). This value is hardcoded in the formula and is not exposed as a user input cell. If a different pulse duration is used experimentally, the formula in `J14` must be edited directly.

4. **Linear regime approximation:** The excitation fraction formula `fexc = σ·Φ` is valid in the weak-field (linear) limit where `fexc << 1`. For `<fexc>` approaching or exceeding ~0.5, saturation effects become significant and the full exponential expression `fexc = 1 − e^(−σΦ)` should be used instead.

5. **Spot size convention:** `B5` and `B6` are listed as FWHM values. The beam area in `L3` uses these as full diameters (dividing by 2 to get radii), treating the beam as a uniform ellipse. No Gaussian correction factor is applied.
