// ===============================
// 1. Define AOI (Ahmedabad)
// ===============================
// var aoi = ee.Geometry.Rectangle([72.45, 22.9, 72.75, 23.1]);

var aoi = ee.Geometry.Rectangle([72.47, 22.88, 72.72, 23.12]);

// ===============================
// 2. Time Range (60 days)
// ===============================
var endDate = ee.Date(Date.now());
// var startDate = endDate.advance(-60, 'day');
// 10 years of data
// var startDate = endDate.advance(-7300, 'day');
// data onwards july, 2018 ----------------------------------------------------------
var startDate = ee.Date('2018-07-11');


// ===============================
// 3. Safe Extraction Function (ES5 Compatible)
// ===============================
function extractMean(image, bandName, scaleVal) {
  var mean = image.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: aoi,
    scale: scaleVal,
    maxPixels: 1e13
  });

  var value = mean.get(bandName);
  value = ee.Algorithms.If(ee.Algorithms.IsEqual(value, null), -999, value);

  var properties = ee.Dictionary({
    'time': image.get('system:time_start')
  }).set(bandName, value);

  return ee.Feature(null, properties);
}

// extract mean

function extractMean(image, bandName, scaleVal) {
  var mean = image.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: aoi,
    scale: scaleVal,
    maxPixels: 1e13
  });

  var value = mean.get(bandName);
  value = ee.Algorithms.If(ee.Algorithms.IsEqual(value, null), -999, value);

  // ✅ Convert milliseconds → readable date string
  var timestamp = ee.Number(image.get('system:time_start'));
  var dateStr = ee.Date(timestamp).format('YYYY-MM-dd');

  var properties = ee.Dictionary({
    'time': timestamp,
    'date': dateStr          // ← Add this human-readable column
  }).set(bandName, value);

  // return ee.Feature(null, properties);
  return ee.Feature(aoi, properties);
}
// ===============================
// 4. MODIS LST (8-day)
// ===============================
var lstFC = ee.ImageCollection("MODIS/061/MOD11A2")
  .filterBounds(aoi)
  .filterDate(startDate, endDate)
  .select('LST_Day_1km')
  .map(function(img) {
    // ✅ Cast back to ee.Image after multiply/subtract to preserve image type
    var lstImg = ee.Image(img.multiply(0.02).subtract(273.15)).rename('LST');
    lstImg = lstImg.set('system:time_start', img.get('system:time_start'));
    return extractMean(lstImg, 'LST', 1000);
  });

// ===============================
// 5. NDVI (Sentinel-2) — MONSOON FILTERED
// ===============================
var ndviFC = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
  .filterBounds(aoi)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
  // ✅ Split into two collections then merge — most reliable approach
  .map(function(img) {
    var month = ee.Date(img.get('system:time_start')).get('month');
    // Keep only non-monsoon months (not 6,7,8,9)
    var isMonsoon = month.gte(6).and(month.lte(9));
    // Set a property to flag monsoon images
    return img.set('is_monsoon', isMonsoon);
  })
  // ✅ Filter out monsoon flagged images
  .filter(ee.Filter.eq('is_monsoon', 0))
  .map(function(img) {
    var qa = img.select('QA60');
    var cloudBitMask = 1 << 10;
    var cirrusBitMask = 1 << 11;
    var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
                 .and(qa.bitwiseAnd(cirrusBitMask).eq(0));

    var ndviImg = ee.Image(img.updateMask(mask)
                  .normalizedDifference(['B8', 'B4'])).rename('NDVI');
    ndviImg = ndviImg.set('system:time_start', img.get('system:time_start'));
    return extractMean(ndviImg, 'NDVI', 10);
  });
// ===============================
// 6. NO2 (Sentinel-5P)
// ===============================
var no2FC = ee.ImageCollection("COPERNICUS/S5P/NRTI/L3_NO2")
  .filterBounds(aoi)
  .filterDate(startDate, endDate)
  .select('NO2_column_number_density')
  .map(function(img) {
    // ✅ Cast back to ee.Image after rename
    var no2Img = ee.Image(img.rename('NO2'));
    no2Img = no2Img.set('system:time_start', img.get('system:time_start'));
    return extractMean(no2Img, 'NO2', 1000);
  });

// ===============================
// 7. Export CSVs
// ===============================
Export.table.toDrive({
  collection: ee.FeatureCollection(lstFC),
  description: 'Ahmedabad_LST_TS',
  fileFormat: 'CSV'
});

Export.table.toDrive({
  collection: ee.FeatureCollection(ndviFC),
  description: 'Ahmedabad_NDVI_TS',
  fileFormat: 'CSV'
});

Export.table.toDrive({
  collection: ee.FeatureCollection(no2FC),
  description: 'Ahmedabad_NO2_TS',
  fileFormat: 'CSV'
});