# Figure Captions

### Figure 1. Spatial model of deposit thickness and borehole exploration networks
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), medium variability scenario (target CV = 25%, actual CV = 25.0%), number of boreholes $n = 16$.
* **Panels**:
  * (a) Quasi-regular grid network with random nodal jitter ($\\le 10\\%$ of grid step);
  * (b) Clustered borehole network (centers located $\\ge 80$ m from deposit boundaries);
  * (c) Preferential sampling network with sampling density proportional to squared thickness ($w \\propto T^2$, $k = 2$).
* **Elements**: Background grayscale shading represents continuous thickness field $T(x, y)$ [m]; black markers denote borehole collars; solid thin lines delineate Voronoi influence polygon boundaries clipped by the deposit perimeter.

---

### Figure 2. Box plots of relative error of reserves estimation across network configurations
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), medium variability scenario (CV = 25%), number of boreholes $n = 16$, 1,000 independent simulation repeats per scenario.
* **Box Plot Definition**: Center line represents sample median; lower and upper box hinges represent first and third quartiles (25th and 75th percentiles); whiskers extend to the 5th and 95th percentiles of the distribution without outlier markers.
* **Methods**: Shaded hatched boxes denote the simple arithmetic mean method; open dotted boxes denote the Voronoi polygon area-weighted method. Dashed horizontal line indicates zero relative error ($e = 0\\%$).

---

### Figure 3. Root mean square error (RMSE) of reserves estimation as a function of borehole count
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), medium variability scenario (CV = 25%), 1,000 independent repeats per point. Both panels share identical vertical axis scaling.
* **Panels**:
  * (a) Non-preferential exploration geometries: Regular, Random, and Clustered networks;
  * (b) Preferential exploration geometries: Linear ($k = 1$) and Quadratic ($k = 2$) preferential sampling.
* **Methods**: Solid lines with filled markers denote simple arithmetic mean estimation; dashed lines with open white markers denote Voronoi area-weighted estimation.

---

### Figure 4. Reserves estimation bias under preferential sampling across variability scenarios
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), 1,000 independent repeats per scenario. Solid horizontal line denotes zero bias ($\mathbb{E}[e] = 0\\%$).
* **Panels**:
  * (a) Linear preferential sampling ($k = 1$);
  * (b) Quadratic preferential sampling ($k = 2$).
* **Methods**: Filled markers denote arithmetic mean; open white markers denote Voronoi weighting. Line styles distinguish variability levels: dotted (Low CV = 10%), dashed (Medium CV = 25%), solid (High CV = 50%).

---

### Figure 5. Comparison of reserves estimation bias between baseline and neutral deposit field modes
* **Conditions**: Rectangular deposit contour (1,000 × 800 m), medium variability scenario (CV = 25%), number of boreholes $n = 16$, 1,000 independent repeats per configuration.
* **Bars and Error Bars**: Grouped bars display sample mean bias $\mathbb{E}[e]$ [%]; error bars denote non-parametric 95% bootstrap confidence intervals computed from 5,000 resamples.
* **Modes**: Diagonal hatching indicates the baseline field mode (`edge_thin`); cross hatching indicates the neutral control field mode (`neutral`). Shaded bars denote arithmetic mean; white bars denote Voronoi area-weighting.
