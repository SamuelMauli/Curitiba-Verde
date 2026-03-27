"""
CwbVerde — Land Use Classifier v3
Key fixes vs previous version:
  - Auto-sample training data from strict spectral thresholds (no hardcoded GPS coords)
  - No per-image normalization (was destroying discriminative power — raw SR values work better)
  - Sensor-specific RF models: L5 for 2000-2012, L8/9 for 2013+
  - Hard post-processing water constraint (MNDWI must be > threshold to stay water)
  - Temporal gap-filling + 3-yr majority vote smoothing
  - 14 features: 6 raw bands + NDVI + NDWI + NDBI + MNDWI + EVI + BSI + SAVI + NBI
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report
import joblib
from pipeline.config import DATA_DIR

np.random.seed(42)

RAW_DIR   = DATA_DIR / "raw"
CLASS_DIR = DATA_DIR / "classification"
MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
CLASS_DIR.mkdir(parents=True, exist_ok=True)

LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = -49.40, -25.65, -49.15, -25.33

CLASSES = {1: "water", 2: "dense_veg", 3: "light_veg", 4: "urban", 5: "bare_soil"}

L5_TRAIN_YEARS  = [2000, 2005, 2010]   # Landsat 5 TM
L89_TRAIN_YEARS = [2015, 2020, 2023]   # Landsat 8/9 OLI

N_SAMPLES_PER_CLASS_PER_YEAR = 4000   # auto-samples per class per training year

FEATURE_NAMES = [
    "blue", "green", "red", "nir", "swir1", "swir2",  # 6 raw bands
    "ndvi", "ndwi", "ndbi", "mndwi",                  # classic indices
    "evi", "bsi", "savi", "nbi",                       # additional indices
]


# ------------------------------------------------------------------
# Feature extraction — NO per-image normalization
# Raw surface reflectance + spectral indices
# ------------------------------------------------------------------
def extract_features(composite_path):
    """
    Extract 14 features from a composite.
    Uses raw surface reflectance (already in physical [0,1] range from GEE).
    No per-image normalization — absolute values are discriminative.
    """
    with rasterio.open(str(composite_path)) as src:
        blue  = src.read(1).astype(np.float64)
        green = src.read(2).astype(np.float64)
        red   = src.read(3).astype(np.float64)
        nir   = src.read(4).astype(np.float64)
        swir1 = src.read(5).astype(np.float64)
        swir2 = src.read(6).astype(np.float64)
        transform = src.transform
        h, w = src.height, src.width

    np.seterr(divide="ignore", invalid="ignore")

    # Indices — all ratio-based, sensor-agnostic
    ndvi  = np.where((nir + red) != 0,    (nir - red)    / (nir + red),    0)
    ndwi  = np.where((green + nir) != 0,  (green - nir)  / (green + nir),  0)
    ndbi  = np.where((swir1 + nir) != 0,  (swir1 - nir)  / (swir1 + nir),  0)
    mndwi = np.where((green + swir1) != 0,(green - swir1)/ (green + swir1), 0)

    # EVI — better than NDVI in dense forest (uses raw SR values)
    evi_d = nir + 6 * red - 7.5 * blue + 1
    evi   = np.where(evi_d != 0, 2.5 * (nir - red) / evi_d, 0)
    evi   = np.clip(evi, -1, 1)

    # BSI — Bare Soil Index
    bsi_n = (swir1 + red) - (nir + blue)
    bsi_d = (swir1 + red) + (nir + blue)
    bsi   = np.where(bsi_d != 0, bsi_n / bsi_d, 0)

    # SAVI — Soil-Adjusted Vegetation Index (L=0.5)
    savi_d = nir + red + 0.5
    savi   = np.where(savi_d != 0, 1.5 * (nir - red) / savi_d, 0)

    # NBI — New Built-up Index
    nbi_n = red * swir1
    nbi_d = nir
    nbi   = np.where(nbi_d != 0, nbi_n / nbi_d, 0)
    nbi   = np.clip(nbi, 0, 5)

    features = np.stack([
        blue, green, red, nir, swir1, swir2,
        ndvi, ndwi, ndbi, mndwi, evi, bsi, savi, nbi,
    ], axis=0)  # shape: (14, h, w)
    return features, transform, h, w


# ------------------------------------------------------------------
# Auto-sampling — generate training data from strict spectral rules
# This avoids hardcoded GPS coordinates that can land on wrong pixels
# ------------------------------------------------------------------
def auto_sample_year(composite_path, n_per_class=N_SAMPLES_PER_CLASS_PER_YEAR, verbose=True):
    """
    Generate training samples from high-confidence spectral pixels.
    Thresholds derived from published Landsat surface reflectance literature
    and validated for Curitiba's land cover types.
    """
    features, transform, h, w = extract_features(composite_path)
    year = int(Path(composite_path).stem.split("_")[1])

    f = features  # shape: (14, h, w)
    ndvi  = f[6]; ndwi = f[7]; ndbi = f[8]; mndwi = f[9]
    evi   = f[10]; bsi = f[11]; savi = f[12]; nbi = f[13]
    nir   = f[3]; green = f[1]; swir1 = f[4]

    # Valid pixel mask (exclude nodata / extreme values)
    valid = (
        np.isfinite(nir) & np.isfinite(ndvi) &
        (nir > -0.3) & (nir < 1.2) &
        (green > -0.3) & (swir1 > -0.3)
    )

    # ---------------------------------------------------------------
    # High-confidence spectral masks
    # Thresholds calibrated from actual Curitiba spectral analysis:
    #   MNDWI median=-0.49, NDBI median=-0.08, NDVI median=0.50
    #   MNDWI>0.20 = only top ~1.2% of pixels (real open water)
    #   NDVI>0.60  = top ~35% (dense forest)
    #   NDBI>0.03  = top ~40% (urban/impervious)
    # ---------------------------------------------------------------

    # 1. WATER — open water bodies (clear + turbid)
    #    Primary: MNDWI > 0.12 (lowered from 0.20 to catch turbid Curitiba rivers)
    #    NIR < 0.09: water absorbs NIR strongly
    #    green > 0.02: avoids dark shadows
    water_mask = (
        valid &
        (mndwi > 0.12) & (nir < 0.09) & (green > 0.02)
    )

    # 2. DENSE VEGETATION — mature forest, closed canopy
    #    Unchanged — already performs well
    dense_mask = (
        valid &
        (ndvi > 0.62) & (evi > 0.32) & (ndbi < -0.20) &
        (~water_mask)
    )

    # 3. URBAN — roads, buildings, concrete, mixed impervious
    #    NDBI > -0.03: widened from 0.03 to capture urban+sparse-tree pixels
    #    NDVI < 0.32: includes residential areas with street trees
    #    MNDWI < -0.12: dry surfaces
    #    KEY FIX: was NDBI>0.03 & NDVI<0.22 — too strict, missed urban-with-trees
    urban_mask = (
        valid &
        (ndbi > -0.03) & (ndvi < 0.32) & (mndwi < -0.12) &
        (~water_mask) & (~dense_mask)
    )

    # 4. BARE SOIL — exposed BROWN/REDDISH earth, construction sites
    #    Exclude bright white/grey rooftops (industrial buildings) — those are urban
    #    red > green > blue confirms brownish soil color, NOT white concrete
    #    blue < 0.14: excludes bright white concrete / industrial rooftops
    red = f[2]; blue_b = f[0]
    bare_mask = (
        valid &
        (ndvi < 0.12) & (bsi > 0.05) & (mndwi < -0.25) &
        (red > blue_b) &           # reddish-brown, not white (red > blue)
        (blue_b < 0.14) &          # not bright white concrete/rooftop
        (~water_mask) & (~dense_mask) & (~urban_mask)
    )

    # 5. LIGHT VEGETATION — real green areas: parks, fields, gardens
    #    STRICT thresholds — prevents urban-with-trees from leaking in:
    #    NDVI > 0.30 (raised from 0.18 — excludes sparse urban vegetation)
    #    NDBI < -0.08 (tightened from -0.02 — requires dominant green signal)
    #    EVI > 0.14 (new — confirms actual photosynthetic activity)
    #    KEY FIX: previous NDVI>0.18 & NDBI<-0.02 was capturing 27% urban pixels
    lightveg_mask = (
        valid &
        (ndvi > 0.30) & (ndvi < 0.62) &
        (ndbi < -0.08) & (evi > 0.14) & (mndwi < 0.08) &
        (~water_mask) & (~dense_mask) & (~urban_mask) & (~bare_mask)
    )

    masks = {1: water_mask, 2: dense_mask, 3: lightveg_mask, 4: urban_mask, 5: bare_mask}

    # Flatten features → (h*w, 14)
    feat_flat = features.reshape(14, -1).T

    X_list, y_list = [], []
    for cid, mask in masks.items():
        idx = np.where(mask.ravel())[0]
        if verbose:
            print(f"      class {CLASSES[cid]:10s}: {len(idx):6,} candidates", end="")
        if len(idx) == 0:
            if verbose:
                print()
            continue
        if len(idx) > n_per_class:
            idx = np.random.choice(idx, n_per_class, replace=False)
        samples = feat_flat[idx]
        # Remove NaN rows
        valid_rows = ~np.any(np.isnan(samples), axis=1)
        samples = samples[valid_rows]
        if verbose:
            print(f" → {len(samples):,} sampled")
        X_list.append(samples)
        y_list.extend([cid] * len(samples))

    if not X_list:
        return np.zeros((0, 14)), np.zeros(0, dtype=int)
    return np.vstack(X_list), np.array(y_list)


def build_training_data(train_years, label=""):
    """Build training dataset from multiple years."""
    X_all, y_all = [], []
    for year in train_years:
        path = RAW_DIR / f"composite_{year}.tif"
        if not path.exists():
            print(f"    WARNING: composite_{year}.tif not found, skipping")
            continue
        print(f"    Year {year}:")
        X, y = auto_sample_year(path)
        if len(X) > 0:
            X_all.append(X)
            y_all.append(y)

    if not X_all:
        raise RuntimeError(f"No training data for {label}")

    X = np.vstack(X_all)
    y = np.concatenate(y_all)
    print(f"\n  Total {label}: {len(X):,} samples")
    for cid, cname in CLASSES.items():
        print(f"    {cname:12s}: {(y == cid).sum():6,}")
    return X, y


# ------------------------------------------------------------------
# Model training
# ------------------------------------------------------------------
def train_rf(X, y, label=""):
    """Train a calibrated Random Forest."""
    rf = RandomForestClassifier(
        n_estimators=500,
        max_depth=25,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    print(f"\n  Fitting RF {label} ({len(X):,} samples, {X.shape[1]} features)...")
    rf.fit(X, y)

    # 5-fold CV on subset for speed
    sub = min(10_000, len(X))
    idx = np.random.choice(len(X), sub, replace=False)
    scores = cross_val_score(rf, X[idx], y[idx], cv=5, scoring="f1_macro", n_jobs=-1)
    print(f"  CV F1-macro: {scores.mean():.4f} ± {scores.std():.4f}")

    imp = rf.feature_importances_
    top = np.argsort(imp)[::-1][:6]
    print(f"  Top features: " + ", ".join(f"{FEATURE_NAMES[i]}={imp[i]:.3f}" for i in top))

    print("\n  Full classification report (train set):")
    y_pred = rf.predict(X[idx])
    report = classification_report(y[idx], y_pred,
                                   target_names=[CLASSES[i] for i in sorted(CLASSES)],
                                   zero_division=0)
    for line in report.split("\n"):
        print("    " + line)

    return rf


# ------------------------------------------------------------------
# Classify one year
# ------------------------------------------------------------------
def classify_year(rf, composite_path, year):
    """
    Classify one composite using RF predictions + hard post-processing rules.
    Hard rules fix obvious misclassifications the ML can't always catch.
    """
    features, transform, h, w = extract_features(composite_path)

    X_all = features.reshape(14, -1).T  # (h*w, 14)
    nan_mask  = np.any(np.isnan(X_all), axis=1)
    zero_mask = np.all(X_all[:, :6] == 0, axis=1)
    nodata_mask = nan_mask | zero_mask

    valid_mask = ~nodata_mask
    X_valid = X_all[valid_mask]

    predictions = rf.predict(X_valid)

    result = np.zeros(h * w, dtype=np.uint8)
    result[valid_mask] = predictions
    classification = result.reshape(h, w)

    # ---------------------------------------------------------------
    # Hard post-processing rules
    # These correct systematic ML errors using unambiguous thresholds
    # ---------------------------------------------------------------
    blue  = features[0]
    green = features[1]
    ndvi  = features[6]
    mndwi = features[9]
    ndbi  = features[8]
    nir   = features[3]
    evi   = features[10]
    nbi   = features[13]

    # Rule 1: Water HARD constraint — must have MNDWI > 0.15 AND NIR < 0.12 AND green > 0.02
    #   Calibrated: MNDWI > 0.15 selects ~1.5% of Curitiba pixels (real water bodies)
    false_water = (classification == 1) & ((mndwi < 0.15) | (nir > 0.12) | (green < 0.02))
    classification[false_water & (ndvi > 0.35)] = 2  # → dense veg
    classification[false_water & (ndvi > 0.15) & (ndvi <= 0.35)] = 3  # → light veg
    classification[false_water & (ndbi > 0.05) & (ndvi <= 0.15)] = 4  # → urban
    classification[false_water & (ndbi <= 0.05) & (ndvi <= 0.15)] = 5  # → bare soil

    # Rule 2: Very high NDVI must be dense vegetation
    #   NDVI > 0.65 → definitely not urban/bare soil
    def_forest = (ndvi > 0.65) & (classification != 1)
    classification[def_forest] = 2

    # Rule 3: Very strong water signal → force water
    def_water = (mndwi > 0.35) & (nir < 0.08)
    classification[def_water] = 1

    # Rule 5: Light veg with urban spectral signal → urban
    #   Fixes: urban areas with street trees / small gardens misclassified as light_veg
    #   NDBI > -0.06: vegetation signal not dominant (mixed urban+tree pixel)
    #   NDVI < 0.35: not genuinely vegetated
    #   NBI > 0.08: built-up materials confirmed (red*swir1/nir ratio)
    urban_correction = (
        (classification == 3) &
        (ndbi > -0.06) &
        (ndvi < 0.35) &
        (nbi > 0.08)
    )
    classification[urban_correction] = 4

    # Rule 6: Bare soil with bright/neutral signature → urban (industrial rooftops)
    #   Industrial buildings have white/beige roofs: high reflectance all bands
    #   True bare soil is brown: red > blue, blue relatively low
    #   Bright (blue > 0.12): concrete, asphalt, rooftop → urban, NOT soil
    #   OR strong NDBI > 0.05: clearly built-up material → urban
    false_bare = (
        (classification == 5) &
        ((blue > 0.12) | (ndbi > 0.05))
    )
    classification[false_bare] = 4

    # Rule 4: Reset nodata
    classification[nodata_mask.reshape(h, w)] = 0

    # Spatial mode filter 3×3 (remove salt-and-pepper noise)
    from scipy.ndimage import generic_filter

    def _mode(v):
        v = v[v > 0].astype(int)
        return (np.bincount(v, minlength=6)[1:].argmax() + 1) if len(v) else 0

    classification = generic_filter(
        classification.astype(float), _mode, size=3
    ).astype(np.uint8)
    classification[nodata_mask.reshape(h, w)] = 0  # Re-apply nodata

    # Save
    tfm = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, w, h)
    out = CLASS_DIR / f"classification_{year}.tif"
    with rasterio.open(str(out), "w",
                       driver="GTiff", height=h, width=w,
                       count=1, dtype="uint8",
                       crs=CRS.from_epsg(4326),
                       transform=tfm, nodata=0) as dst:
        dst.write(classification, 1)

    return classification


def print_stats(classification, year):
    valid = classification[classification > 0]
    total = len(valid)
    if total == 0:
        return
    parts = []
    for cid, cname in CLASSES.items():
        pct = (valid == cid).sum() / total * 100
        ha = (valid == cid).sum() * 0.09
        parts.append(f"{cname}={pct:.1f}% ({ha:.0f}ha)")
    print("    " + "  ".join(parts))


# ------------------------------------------------------------------
# Temporal smoothing + gap filling
# ------------------------------------------------------------------
def apply_temporal_smoothing(years):
    """
    1. Temporal gap-fill (fill nodata from neighbors → consistent spatial coverage)
    2. 3-year majority vote (correct single-year sensor noise)
    """
    print("\n--- Temporal smoothing ---")
    data = {}
    for year in years:
        path = CLASS_DIR / f"classification_{year}.tif"
        if path.exists():
            with rasterio.open(str(path)) as src:
                data[year] = src.read(1).copy()

    sorted_years = sorted(data.keys())
    n = len(sorted_years)
    first = data[sorted_years[0]]
    h, w = first.shape

    stack = np.zeros((n, h, w), dtype=np.uint8)
    for i, y in enumerate(sorted_years):
        stack[i] = data[y]

    # Step 1: Gap-filling (forward then backward pass)
    gf = stack.copy()
    for i in range(1, n):
        nodata = gf[i] == 0
        gf[i][nodata] = gf[i - 1][nodata]
    for i in range(n - 2, -1, -1):
        nodata = gf[i] == 0
        gf[i][nodata] = gf[i + 1][nodata]

    filled_pcts = [(stack[i] == 0).sum() / (h * w) * 100 for i in range(n)]
    bad_years = [(sorted_years[i], filled_pcts[i]) for i in range(n) if filled_pcts[i] > 5]
    if bad_years:
        print("  Years with significant nodata (gap-filled from neighbors):")
        for yr, pct in bad_years:
            print(f"    {yr}: {pct:.0f}% nodata filled")

    # Step 2: 3-year majority vote on gap-filled data
    smoothed = np.zeros_like(stack)
    for i, year in enumerate(sorted_years):
        t0 = max(0, i - 1)
        t1 = min(n, i + 2)
        w3 = gf[t0:t1]  # (2 or 3, h, w)
        T = w3.shape[0]

        if T == 1:
            s = w3[0].copy()
        elif T == 2:
            a, b = w3[0], w3[1]
            cur = w3[i - t0]
            s = np.where((a == b) & (a > 0), a, cur)
        else:
            a, b, c = w3[0], w3[1], w3[2]
            cur = w3[i - t0]
            s = np.where((a == b) & (a > 0), a,
                np.where((a == c) & (a > 0), a,
                np.where((b == c) & (b > 0), b, cur)))

        smoothed[i] = s.astype(np.uint8)

    # Overwrite classification files
    for i, year in enumerate(sorted_years):
        path = CLASS_DIR / f"classification_{year}.tif"
        with rasterio.open(str(path)) as src:
            meta = src.meta.copy()
        with rasterio.open(str(path), "w", **meta) as dst:
            dst.write(smoothed[i], 1)

    return smoothed, sorted_years


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    print("=" * 65)
    print("CwbVerde — Classifier v3 (auto-sampling, no normalization)")
    print("=" * 65)

    # --- Train L5 model ---
    print("\n[1/2] Landsat 5 model (2000-2012)")
    avail5 = [y for y in L5_TRAIN_YEARS if (RAW_DIR / f"composite_{y}.tif").exists()]
    print(f"  Training years: {avail5}")
    X5, y5 = build_training_data(avail5, "L5")
    rf5 = train_rf(X5, y5, "L5")

    # --- Train L8/9 model ---
    print("\n[2/2] Landsat 8/9 model (2013+)")
    avail89 = [y for y in L89_TRAIN_YEARS if (RAW_DIR / f"composite_{y}.tif").exists()]
    print(f"  Training years: {avail89}")
    X89, y89 = build_training_data(avail89, "L8/9")
    rf89 = train_rf(X89, y89, "L8/9")

    # Save models
    joblib.dump(rf5,  str(MODEL_DIR / "model_l5.joblib"))
    joblib.dump(rf89, str(MODEL_DIR / "model_l89.joblib"))
    print(f"\nModels saved → {MODEL_DIR}/")

    # --- Classify all years ---
    print("\n--- Classifying all years ---")
    all_composites = sorted(RAW_DIR.glob("composite_*.tif"))
    years_done = []

    for comp in all_composites:
        year = int(comp.stem.split("_")[1])
        if year > 2024:
            continue
        rf = rf5 if year <= 2012 else rf89
        sensor = "L5" if year <= 2012 else "L8/9"
        print(f"\n  {year} ({sensor}):")
        cls = classify_year(rf, comp, year)
        if cls is not None:
            print_stats(cls, year)
            years_done.append(year)

    # --- Temporal smoothing ---
    smoothed, sorted_years = apply_temporal_smoothing(years_done)

    # --- Summary ---
    print("\n--- Post-smoothing classification summary ---")
    import pandas as pd
    rows = []
    for i, year in enumerate(sorted_years):
        cls = smoothed[i]
        valid = cls[cls > 0]
        total = len(valid)
        if total == 0:
            continue
        row = {"year": year}
        for cid, cname in CLASSES.items():
            row[f"{cname}_pct"] = float((valid == cid).sum() / total * 100)
            row[f"{cname}_ha"]  = float((valid == cid).sum() * 0.09)
        rows.append(row)

    if rows:
        df = pd.DataFrame(rows).sort_values("year")
        out = DATA_DIR / "stats" / "classification_summary.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(str(out), index=False)

        cols = ["year", "water_pct", "dense_veg_pct", "light_veg_pct", "urban_pct", "bare_soil_pct"]
        print(df[cols].to_string(index=False))
        print(f"\nSaved: {out}")

    print(f"\nDone — {len(years_done)} years classified.")


if __name__ == "__main__":
    main()
