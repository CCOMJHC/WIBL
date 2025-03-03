import Map from "./ol/Map.js";
import OSM from "./ol/source/OSM.js";
import TileLayer from "./ol/layer/Tile.js";
import View from "./node_modules/ol/View.js";

export const olMap = new Map({
  target: 'map',
  layers: [
    new TileLayer({
      source: new OSM(),
    }),
  ],
  view: new View({
    center: [0, 0],
    zoom: 2,
  }),
});