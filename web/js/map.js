/*
  Shared world map: drawing, zoom/pan, highlight and ring marker.
  Uses the global d3 (vendor/d3.min.js).
*/

export const CONTINENTS = ['Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania'];

// Geographic bounding box per continent: [west, south, east, north].
// Used to zoom the map in continent mode.
const CONTINENT_BOX = {
  'Africa': [-20, -36, 52, 38],
  'Asia': [25, -11, 150, 78],
  'Europe': [-25, 34, 65, 72],
  'North America': [-170, 7, -50, 74],
  'South America': [-82, -56, -34, 13],
  'Oceania': [110, -48, 180, 12],
};

const MAP_WIDTH = 960;
const MAP_HEIGHT = 500;

let mapGroup; // <g> that is zoomed and panned
let ring; // circle that marks the current country
let projection;
let zoomBehavior;

// Id used to find a country's <path> on the map.
export function featureDomId(feature) {
  return 'f' + (feature.id || feature.properties.name.replace(/\W/g, ''));
}

export function drawMap(features) {
  const svg = d3.select('#map');
  projection = d3.geoNaturalEarth1().fitSize([MAP_WIDTH, MAP_HEIGHT], { type: 'Sphere' });
  const path = d3.geoPath(projection);

  mapGroup = svg.append('g');

  mapGroup.append('g')
    .selectAll('path')
    .data(features)
    .join('path')
    .attr('d', path)
    .attr('id', featureDomId);

  ring = mapGroup.append('circle')
    .attr('id', 'ring')
    .attr('r', 9)
    .attr('stroke-width', 2);

  // Zoom and pan. Keep the ring the same size on screen while zooming.
  zoomBehavior = d3.zoom()
    .scaleExtent([1, 40])
    .translateExtent([[0, 0], [MAP_WIDTH, MAP_HEIGHT]])
    .on('zoom', (event) => {
      mapGroup.attr('transform', event.transform);
      ring
        .attr('r', 9 / event.transform.k)
        .attr('stroke-width', 2 / event.transform.k);
    });

  svg.call(zoomBehavior);
}

// Zoom transform that frames a whole continent.
export function continentView(name) {
  const [west, south, east, north] = CONTINENT_BOX[name];
  const middle = (south + north) / 2;

  const corners = [
    [west, south], [west, north],
    [east, south], [east, north],
    [west, middle], [east, middle],
  ].map(projection);

  const x0 = d3.min(corners, (p) => p[0]);
  const x1 = d3.max(corners, (p) => p[0]);
  const y0 = d3.min(corners, (p) => p[1]);
  const y1 = d3.max(corners, (p) => p[1]);

  const scale = Math.min(MAP_WIDTH / (x1 - x0), MAP_HEIGHT / (y1 - y0)) * 0.92;

  return d3.zoomIdentity
    .translate(MAP_WIDTH / 2 - scale * (x0 + x1) / 2, MAP_HEIGHT / 2 - scale * (y0 + y1) / 2)
    .scale(scale);
}

// Highlights and rings a country. `continent` is optional: if set, zoom to
// that continent unless the country would fall outside the view.
export function showCountryOnMap(country, continent) {
  // Highlight the country's shape.
  mapGroup.selectAll('path').classed('hl', false);
  if (country.feature) {
    d3.select('#' + featureDomId(country.feature)).classed('hl', true).raise();
  }

  // Put the ring on it (helps to find very small countries).
  const [x, y] = projection([country.latlng[1], country.latlng[0]]);
  ring.attr('cx', x).attr('cy', y);

  // Continent mode zooms to the continent, unless the country would be
  // outside that view (e.g. Samoa); then show the whole world.
  let view = d3.zoomIdentity;
  if (continent) {
    const candidate = continentView(continent);
    const screenX = candidate.x + candidate.k * x;
    const screenY = candidate.y + candidate.k * y;
    const inside = screenX > 10 && screenX < MAP_WIDTH - 10 && screenY > 10 && screenY < MAP_HEIGHT - 10;
    if (inside) view = candidate;
  }
  d3.select('#map').call(zoomBehavior.transform, view);
}
