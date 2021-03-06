# Monoprice Monolith M1060
Replace `C:\Program Files\EqualizerAPO\config\config.txt` with:
```
Preamp: -6.0dB
GraphicEQ: 10 -84; 20 3.8; 22 3.7; 23 3.7; 25 3.8; 26 3.8; 28 3.8; 30 3.9; 32 3.9; 35 3.9; 37 3.8; 40 3.6; 42 3.3; 45 2.9; 49 2.7; 52 2.7; 56 2.8; 59 2.8; 64 2.8; 68 2.8; 73 2.7; 78 2.6; 83 2.3; 89 1.8; 95 1.4; 102 0.9; 109 0.5; 117 0.0; 125 -0.4; 134 -0.7; 143 -1.0; 153 -1.2; 164 -1.3; 175 -1.6; 188 -1.6; 201 -1.8; 215 -1.9; 230 -1.9; 246 -1.8; 263 -1.6; 282 -1.2; 301 -1.3; 323 -1.5; 345 -1.3; 369 -0.8; 395 -0.4; 423 -0.3; 452 -0.3; 484 -0.3; 518 -0.4; 554 -0.3; 593 -0.6; 635 -0.7; 679 -0.7; 726 -0.5; 777 -0.4; 832 0.1; 890 0.5; 952 0.1; 1019 0.2; 1090 0.2; 1167 -0.0; 1248 0.1; 1336 0.9; 1429 1.0; 1529 1.1; 1636 1.8; 1751 3.2; 1873 4.6; 2004 5.6; 2145 6.0; 2295 6.0; 2455 5.6; 2627 5.7; 2811 6.0; 3008 6.0; 3219 5.6; 3444 5.8; 3685 5.1; 3943 5.0; 4219 6.0; 4514 6.0; 4830 6.0; 5168 6.0; 5530 6.0; 5917 5.9; 6331 5.5; 6775 3.9; 7249 1.3; 7756 0.3; 8299 0.0; 8880 0.0; 9502 0.0; 10167 0.0; 10879 0.0; 11640 0.0; 12455 0.0; 13327 0.0; 14260 0.0; 15258 0.0; 16326 0.0; 17469 0.0; 18692 0.0; 20000 -0.1
```
**OR** if using HeSuVi replace `C:\Program Files\EqualizerAPO\config\HeSuVi\eq.txt` and omit `Preamp: -6.0dB` and instead set Global volume in the UI for both channels to **-60**.

![](https://raw.githubusercontent.com/jaakkopasanen/AutoEq/master/results/Headphone.com/innerfidelity/onear/Monoprice%20Monolith%20M1060/Monoprice%20Monolith%20M1060.png)

# Run 2018-07-27T18:01:49.983841
There results were obtained with parameters:
* `--input_dir="innerfidelity\data\onear\Monoprice Monolith M1060"`
* `--output_dir="results\Headphone.com\innerfidelity\onear\Monoprice Monolith M1060"`
* `--calibration="calibration\innerfidelity_raw_to_headphonecom_raw.csv"`
* `--compensation="headphonecom\resources\headphonecom_compensation.csv"`
* `--bass_boost=4.0`
* `--tilt=0.0`
* `--max_gain=6.0`
* `--treble_f_lower=6000.0`
* `--treble_f_upper=8000.0`
* `--treble_max_gain=0.0`
* `--treble_gain_k=1.0`