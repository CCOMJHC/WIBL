var map = L.map('map').setView([43.13555, -70.9395], 13);
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }).addTo(map);

function determine_range(features) {
    var minDepth = 11000.0;
    var maxDepth = 0.0;
    var minLat = 90.0;
    var maxLat = -90.0;
    var minLon = 180.0;
    var maxLon = -180.0;

    for (var f = 0; f < features.length; ++f) {
        lat = features[f].geometry.coordinates[1];
        lon = features[f].geometry.coordinates[0];
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
        const depth = features[f].properties.depth;
        if (depth < 0.0 || depth > 11000.0)
            continue;
        if (depth < minDepth)
            minDepth = depth;
        if (depth > maxDepth)
            maxDepth = depth;
    }
    return { 'minDepth': minDepth, 'maxDepth': maxDepth, 'minLon': minLon, 'maxLon': maxLon, 'minLat': minLat, 'maxLat': maxLat }
}

function combineRanges(a, b) {
    var r = a;
    if (b.minDepth < r.minDepth) r.minDepth = b.minDepth;
    if (b.maxDepth > r.maxDepth) r.maxDepth = b.maxDepth;
    if (b.minLat < r.minLat) r.minLat = b.minLat;
    if (b.maxLat > r.maxLat) r.maxLat = b.maxLat;
    if (b.minLon < r.minLon) r.minLon = b.minLon;
    if (b.maxLon > r.maxLon) r.maxLon = b.maxLon;
    return r;
}

function decToHex(dec) {
    return dec.toString(16);
}
  
function padToTwo(str) {
    return str.padStart(2, '0');
}
  
function rgbToHex(r, g, b) {
    const hexR = padToTwo(decToHex(r));
    const hexG = padToTwo(decToHex(g));
    const hexB = padToTwo(decToHex(b));
  
    return `#${hexR}${hexG}${hexB}`;
}

function addFiles() {
    var filelist = document.getElementById('file-name').files;
    var range = { 'minDepth': 11000.0, 'maxDepth': 0.0, 'minLat': 90.0, 'maxLat': -90.0, 'minLon': 180.0, 'maxLon': -180.0 };
    Object.keys(filelist).forEach(i => {
        const file = filelist[i];
        const reader = new FileReader();
        reader.onload = function(e) {
            const geojson = JSON.parse(e.target.result);
            const fileRange = determine_range(geojson['features']);
            range = combineRanges(range, fileRange);
            L.geoJSON(geojson['features'], {
                pointToLayer: function (feature,latlng) {
                    var marker = {
                        radius: 2,
                        fillColor: "#ff7800",
                        color: "#000",
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8,
                        stroke: false
                    };
                    if (feature.properties.depth < 11000) {
                        const scaleFactor = (feature.properties.depth - range.minDepth)/(range.maxDepth - range.minDepth);
                        const color = evaluate_cmap(scaleFactor, 'rainbow');
                        const colorString = rgbToHex(color[0], color[1], color[2]);
                        marker.fillColor = colorString;
                    } else {
                        marker.fillColor = "#000000";
                        marker.fillOpacity = 0.0;
                    }
                    return L.circleMarker(latlng, marker);
                }
            }).addTo(map);
            const meanLat = (range.minLat + range.maxLat)/2.0;
            const meanLon = (range.minLon + range.maxLon)/2.0;
            map.setView([meanLat, meanLon], 13);
        }
        reader.readAsText(file);
    });
}
