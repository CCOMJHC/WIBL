
export class GeojsonMap {

    olMap = null;
    mapButton = null;
    overlay = null;
    container = null;
    content = null;
    closer = null;

    renderTable(data, container) {
        const tableHTML = `
            <table class="table is-bordered">
                <thead class="is-hidden">
                    <tr>
                        <th> </th>
                        <th> </th>
                    </tr>
                </thead>
                <tbody>
                        ${Object.entries(data)
                            .map(([key, value]) => `<tr>
                                                        <td>${key}</td>
                                                        <td>${value}</td>
                                                    </tr>`).join("")}
                </tbody>
            </table>
        `;
        container.innerHTML = tableHTML;
    }

    getFeaturesExtent(features) {
        let extent = features[0].getGeometry().getExtent();

        for (let feature of features) {
            ol.extent.extend(extent, feature.getGeometry().getExtent());
        }

        return extent;
    }

    calculateZoom(map, features) {
        const extent = this.getFeaturesExtent(features);
        const mapSize = map.getSize();
        const view = map.getView();

        const resolution = view.getResolutionForExtent(extent, mapSize);

        return view.getZoomForResolution(resolution);
    }

    async loadGeojson(map, fileid) {
        let layers = map.getLayers();
        for (let layer of layers.array_) {
            if (layer.className_ !== "ol-layer") {
                map.removeLayer(layer);
            }
        }
        try {
            const res = await fetch(`./saveGeojsonFile/${fileid}`);
            if (!res.ok) {
                throw new Error(`HTTP error! Status: ${res.status}`);
            }
            const geojsonObject = await res.json();

            const geojsonFormat = new ol.format.GeoJSON();
            const features = geojsonFormat.readFeatures(geojsonObject.geojson, {
                featureProjection: 'EPSG:4326'
            });

            var avg_X = 0;
            var avg_Y = 0;

            let all_X_Coordinates = 0;
            let all_Y_Coordinates = 0;

            for (let feature of features) {
                let coordinates = feature.getGeometry().getCoordinates();
                all_X_Coordinates += coordinates[0];
                all_Y_Coordinates += coordinates[1];
            }

            avg_X = all_X_Coordinates / features.length;
            avg_Y = all_Y_Coordinates / features.length;

            const vectorSource = new ol.source.Vector({
                features: features
            });

            const vectorLayer = new ol.layer.Vector({
                source: vectorSource,
                className: `ol-${fileid}`
            });

            map.addLayer(vectorLayer);

            map.getView().setCenter([avg_X, avg_Y]);
            const zoom = this.calculateZoom(map, features);
            map.getView().setZoom(zoom == 0 ? zoom: zoom - 1);

            const selectInteraction = new ol.interaction.Select({
                condition: ol.events.condition.click,
                layers: [vectorLayer]
            });

            map.addInteraction(selectInteraction);

            selectInteraction.on('select', (event) => {
                if (event.selected.length > 0) {
                    const feature = event.selected[0];
                    const properties = feature.getProperties();
                    delete properties.geometry;

                    let coordinates = feature.getGeometry().getCoordinates();
                    this.renderTable(properties, this.content);
                    this.overlay.setPosition(coordinates);
                }
            });

            this.closer.onclick = () => {
                this.overlay.setPosition(undefined);
                this.closer.blur();
                selectInteraction.getFeatures().clear();
                return false;
            };
        } catch (error) {
            console.error('Error loading GeoJSON:', error);
        }
    }

    init(geojsonFileTable) {
        this.mapButton = document.getElementById("mapButton");
        this.container = document.getElementById('popup');
        this.content = document.getElementById('popup-content');
        this.closer = document.getElementById('popup-closer');


        mapButton.addEventListener("click", (event) => {
            const files = geojsonFileTable.getSelectedFiles(3);

            const tabs = document.querySelectorAll(".tabs ul li");
            let geoTab;
            tabs.forEach((tab) => {
                if (tab.getAttribute("data-target") === "map") {
                    geoTab = tab;
                }
            });
            geoTab.click();

            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                this.loadGeojson(this.olMap, file);
            }
        });

        this.overlay = new ol.Overlay({
              element: this.container,
              autoPan: {
                  animation: {
                    duration: 250,
                  },
              },
        });

        this.olMap = new ol.Map({
            target: 'map',
            overlays: [this.overlay],
            layers: [
                new ol.layer.Tile({
                  source: new ol.source.OSM(),
                }),
            ],
            view: new ol.View({
                projection: "EPSG:4326",
                center: [0, 0],
                zoom: 0,
            }),
        });
    }
}
