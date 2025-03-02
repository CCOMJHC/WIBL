export function mapCreate() {
    mapboxgl.accessToken = 'pk.eyJ1IjoiZ3QxMDc0IiwiYSI6ImNtN3M0YTl2ODFnNzUyanB1cjA3a2Q1YXUifQ.-RsSlrDnwsBvwDP3OpJjsg';
    const map = new mapboxgl.Map({
        container: 'map', // container ID
        style: 'mapbox://styles/mapbox/streets-v12', // style URL
        center: [-74.5, 40], // starting position [lng, lat]
        zoom: 9, // starting zoom
    });
}

export function mapUpdate(map) {

}