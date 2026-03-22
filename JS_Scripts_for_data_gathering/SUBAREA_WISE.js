// ================================================
// AHMEDABAD SUB-AREA URBAN MONITORING SYSTEM
// LST + NDVI + NO2 per neighborhood
// ================================================

// ================================================
// 1. TIME RANGE
// ================================================
var startDate = ee.Date('2024-01-01');
var endDate   = ee.Date(Date.now());

// ================================================
// 2. SUB-AREAS WITH CORRECTED COORDINATES
//    Each area = 1km radius circle around centroid
// ================================================
var areas = [
  { name: 'Naroda',        zone: 'North-East',      lat: 23.0686, lng: 72.6536 },
  { name: 'Nikol',         zone: 'Upper-East',      lat: 23.050,  lng: 72.660  },
  { name: 'Maninagar',     zone: 'Central-East',    lat: 22.9962, lng: 72.5996 },
  { name: 'Vastral',       zone: 'South-East',      lat: 22.980,  lng: 72.670  },
  { name: 'Gota',          zone: 'North-West',      lat: 23.112,  lng: 72.535  },
  { name: 'Thaltej',       zone: 'Mid-West',        lat: 23.048,  lng: 72.508  },
  { name: 'Satellite',     zone: 'Central-West',    lat: 23.028,  lng: 72.525  },
  { name: 'Prahlad Nagar', zone: 'South-West',      lat: 23.008,  lng: 72.505  },
  { name: 'Motera',        zone: 'Far-North',       lat: 23.098,  lng: 72.592  },
  { name: 'Chandkheda',    zone: 'Upper-Central',   lat: 23.108,  lng: 72.575  },
  { name: 'Sabarmati',     zone: 'Central-Link',    lat: 23.079,  lng: 72.587  },
  { name: 'Ranip',         zone: 'Inner-West-North',lat: 23.077,  lng: 72.558  },
  { name: 'Sarkhej',       zone: 'South-West-Outer',lat: 22.968,  lng: 72.502  },
  { name: 'Vasna',         zone: 'Central-South',   lat: 23.004,  lng: 72.546  },
  { name: 'Juhapura',      zone: 'Inner-South',     lat: 23.018,  lng: 72.518  },
  { name: 'Isanpur',       zone: 'Inner-South-East',lat: 22.978,  lng: 72.598  }
];

// ================================================
// 3. BUILD GEOMETRY PER AREA (1km buffer)
// ================================================
var areaFeatures = ee.FeatureCollection(areas.map(function(a) {
  var pt  = ee.Geometry.Point([a.lng, a.lat]);
  var buf = pt.buffer(1000); // 1km radius
  return ee.Feature(buf, { name: a.name, zone: a.zone });
}));

// ================================================
// 4. EXTRACT MEAN FOR A GIVEN AREA GEOMETRY
// ================================================
function extractForArea(image, bandName, scaleVal, areaGeom, areaName, areaZone) {
  var mean = image.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: areaGeom,
    scale: scaleVal,
    maxPixels: 1e13
  });

  var value = mean.get(bandName);
  value = ee.Algorithms.If(ee.Algorithms.IsEqual(value, null), -999, value);

  var timestamp = ee.Number(image.get('system:time_start'));
  var dateStr   = ee.Date(timestamp).format('YYYY-MM-dd');

  return ee.Feature(null, ee.Dictionary({
    'area':  areaName,
    'zone':  areaZone,
    'date':  dateStr,
    'time':  timestamp
  }).set(bandName, value));
}

// ================================================
// 5. LST — MODIS 8-day per area
// ================================================
var lstFC = ee.FeatureCollection(
  areas.map(function(a) {
    var geom = ee.Geometry.Point([a.lng, a.lat]).buffer(1000);
    var col  = ee.ImageCollection('MODIS/061/MOD11A2')
      .filterBounds(geom)
      .filterDate(startDate, endDate)
      .select('LST_Day_1km');

    return col.map(function(img) {
      var lstImg = ee.Image(img.multiply(0.02).subtract(273.15)).rename('LST');
      lstImg = lstImg.set('system:time_start', img.get('system:time_start'));
      return extractForArea(lstImg, 'LST', 1000, geom, a.name, a.zone);
    });
  })
).flatten();

// ================================================
// 6. NDVI — Sentinel-2 per area (non-monsoon)
// ================================================
var ndviFC = ee.FeatureCollection(
  areas.map(function(a) {
    var geom = ee.Geometry.Point([a.lng, a.lat]).buffer(1000);
    var col  = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterBounds(geom)
      .filterDate(startDate, endDate)
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
      // Exclude monsoon months
      .map(function(img) {
        var month     = ee.Date(img.get('system:time_start')).get('month');
        var isMonsoon = month.gte(6).and(month.lte(9));
        return img.set('is_monsoon', isMonsoon);
      })
      .filter(ee.Filter.eq('is_monsoon', 0));

    return col.map(function(img) {
      var qa            = img.select('QA60');
      var cloudBitMask  = 1 << 10;
      var cirrusBitMask = 1 << 11;
      var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
                   .and(qa.bitwiseAnd(cirrusBitMask).eq(0));

      var ndviImg = ee.Image(
        img.updateMask(mask).normalizedDifference(['B8', 'B4'])
      ).rename('NDVI');
      ndviImg = ndviImg.set('system:time_start', img.get('system:time_start'));
      return extractForArea(ndviImg, 'NDVI', 10, geom, a.name, a.zone);
    });
  })
).flatten();

// ================================================
// 7. NO2 — Sentinel-5P per area
// ================================================
var no2FC = ee.FeatureCollection(
  areas.map(function(a) {
    var geom = ee.Geometry.Point([a.lng, a.lat]).buffer(1000);
    var col  = ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2')
      .filterBounds(geom)
      .filterDate(startDate, endDate)
      .select('NO2_column_number_density');

    return col.map(function(img) {
      var no2Img = ee.Image(img.rename('NO2'));
      no2Img = no2Img.set('system:time_start', img.get('system:time_start'));
      return extractForArea(no2Img, 'NO2', 1000, geom, a.name, a.zone);
    });
  })
).flatten();

// ================================================
// 8. EXPORT CSVs (one file each, area column inside)
// ================================================
Export.table.toDrive({
  collection: lstFC,
  description: 'Ahmedabad_Areas_LST',
  fileFormat: 'CSV'
});

Export.table.toDrive({
  collection: ndviFC,
  description: 'Ahmedabad_Areas_NDVI',
  fileFormat: 'CSV'
});

Export.table.toDrive({
  collection: no2FC,
  description: 'Ahmedabad_Areas_NO2',
  fileFormat: 'CSV'
});

// ================================================
// 9. VISUALIZE AREAS ON MAP (for verification)
// ================================================
Map.centerObject(areaFeatures, 12);
Map.addLayer(areaFeatures, { color: 'FF0000' }, 'Sub-Areas (1km buffer)');