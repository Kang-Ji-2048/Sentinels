// England map: a 3D column per spill of an hour or more (height = hours discharging), a small dot for shorter
// ones, colour = verdict. Selecting a spill flies to it and draws the 10 km rain-check area with its gauges.
import { useEffect, useMemo, useRef, useState } from "react"
import Map, { Marker, NavigationControl, useControl, type MapRef } from "react-map-gl/maplibre"
import { MapboxOverlay, type MapboxOverlayProps } from "@deck.gl/mapbox"
import { ColumnLayer, LineLayer, ScatterplotLayer } from "@deck.gl/layers"
import type { Map as MaplibreMap } from "maplibre-gl"
import { AREA_M, DRY_MM, VERDICT, fmt, hrs, isLong, titleCase, verdictOf, type Gauge, type Site, type Verdict } from "@/lib/data"

const ENGLAND: [[number, number], [number, number]] = [[-5.8, 49.9], [1.9, 55.9]]
const PX_PER_HOUR = 5 // column height in screen pixels per hour, so columns stay readable at any zoom
const SELECTION: [number, number, number, number] = [232, 185, 49, 255]
const NAVY: [number, number, number] = [18, 53, 91]
const wet = (g: Gauge) => g.mm_0_24h_before >= DRY_MM || g.mm_24_48h_before >= DRY_MM
const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches
const englandPadding = () => ({ top: 30, bottom: 30, left: 30, right: 30 })

function DeckOverlay(props: MapboxOverlayProps) {
  const overlay = useControl(() => new MapboxOverlay(props))
  overlay.setProps(props)
  return null
}

/** Restyle CARTO Positron into the Sentinels palette: land, sea, rivers and coastline only. */
function restyle(map: MaplibreMap) {
  for (const l of map.getStyle().layers) {
    if (l.id === "background") map.setPaintProperty(l.id, "background-color", "#D6E4EC")
    else if (l.id === "water") map.setPaintProperty(l.id, "fill-color", "#D6E4EC")
    else if (l.id === "waterway") map.setPaintProperty(l.id, "line-color", "#A9C2D3")
    else if (l.id.startsWith("boundary_country")) map.setPaintProperty(l.id, "line-color", "#B5C2CC")
    else map.setLayoutProperty(l.id, "visibility", "none")
  }
  const water = map.getLayer("water") as { source: string; sourceLayer?: string; filter?: unknown } | undefined
  if (!water || map.getLayer("land")) return
  map.addLayer({ id: "land", type: "fill", source: water.source, "source-layer": "earth", paint: { "fill-color": "#F4F6F2" } }, "water")
  map.addLayer({ id: "coast", type: "line", source: water.source, "source-layer": water.sourceLayer!,
    filter: ["in", ["get", "kind"], ["literal", ["ocean", "sea", "bay", "strait"]]],
    paint: { "line-color": "#7E93A3", "line-width": 0.8 } })
}

export function SpillMap({ sites, selected, focus, showContext, onSelect }: {
  sites: Site[]; selected: Site | null; focus: Site[] | null; showContext: boolean; onSelect: (s: Site | null) => void
}) {
  const ref = useRef<MapRef>(null)
  const [view, setView] = useState({ zoom: 5.5, lat: 53 })
  const [loaded, setLoaded] = useState(false)

  // Fly to the selection, else fit the focused area (a company's spills), else show all of England.
  useEffect(() => {
    const map = ref.current
    if (!map || !loaded) return
    const duration = reducedMotion() ? 0 : 1500
    if (selected) {
      map.flyTo({ center: [selected.lon, selected.lat], zoom: 10.4, pitch: 55, bearing: 0, duration, essential: true,
        padding: { top: 40, bottom: 40, left: 40, right: 40 } })
    } else if (focus?.length) {
      const lons = focus.map(s => s.lon), lats = focus.map(s => s.lat)
      map.fitBounds([[Math.min(...lons) - 0.3, Math.min(...lats) - 0.3], [Math.max(...lons) + 0.3, Math.max(...lats) + 0.3]],
        { padding: englandPadding(), pitch: 45, bearing: 0, duration, maxZoom: 9 })
    } else map.fitBounds(ENGLAND, { padding: englandPadding(), pitch: 45, bearing: 0, duration })
  }, [selected, focus, loaded])

  const layers = useMemo(() => {
    // metres per screen pixel at this zoom, grown a little when zoomed in so columns stay chunky
    const m = (40075016.686 * Math.cos((view.lat * Math.PI) / 180)) / (512 * 2 ** view.zoom) * Math.min(2, 1 + Math.max(0, view.zoom - 6) * 0.25)
    const sel = selected?.id
    const shown = (v: Verdict) => v === "dry_spill_candidate" || showContext
    const fill = (s: Site, a: number): [number, number, number, number] => (s.id === sel ? SELECTION : [...VERDICT[verdictOf(s)].rgb, a])
    const long = sites.filter(s => isLong(s) && shown(verdictOf(s)))
    const short = sites.filter(s => !isLong(s) && shown(verdictOf(s)))
    const gs = selected ? selected.gauges.filter(g => g.lat != null && g.lon != null) : []
    const order = (s: Site) => (verdictOf(s) === "dry_spill_candidate" ? 1 : 0) // dry drawn last, on top
    return [
      new ScatterplotLayer<Site>({ id: "area", data: selected ? [selected] : [], getPosition: s => [s.lon, s.lat], getRadius: AREA_M,
        filled: true, stroked: true, getFillColor: [232, 185, 49, 45], getLineColor: [184, 140, 20, 255], lineWidthMinPixels: 2 }),
      new LineLayer<Gauge>({ id: "links", data: gs, getSourcePosition: () => [selected!.lon, selected!.lat],
        getTargetPosition: g => [g.lon!, g.lat!], getColor: [...NAVY, 180], getWidth: 1.5 }),
      new ScatterplotLayer<Gauge>({ id: "gauges", data: gs, getPosition: g => [g.lon!, g.lat!], radiusUnits: "pixels", getRadius: 7,
        filled: true, stroked: true, lineWidthUnits: "pixels", getLineWidth: 2,
        getFillColor: g => (wet(g) ? [...NAVY, 255] : [255, 255, 255, 255]), getLineColor: [...NAVY, 255] }),
      new ScatterplotLayer<Site>({ id: "short", data: [...short].sort((a, b) => order(a) - order(b)), getPosition: s => [s.lon, s.lat],
        radiusUnits: "pixels", getRadius: s => (s.id === sel ? 7 : verdictOf(s) === "dry_spill_candidate" ? 4.5 : 3.5),
        stroked: true, lineWidthUnits: "pixels", getLineWidth: 1, getLineColor: [255, 255, 255, 230],
        getFillColor: s => fill(s, 220), pickable: true, autoHighlight: true, highlightColor: SELECTION,
        updateTriggers: { getFillColor: sel, getRadius: sel } }),
      new ColumnLayer<Site>({ id: "columns", data: [...long].sort((a, b) => order(a) - order(b)), diskResolution: 24, extruded: true,
        radius: 6 * m, getPosition: s => [s.lon, s.lat], getElevation: s => (s.hours ?? 1) * PX_PER_HOUR * m,
        getFillColor: s => fill(s, verdictOf(s) === "dry_spill_candidate" ? 235 : 150),
        pickable: true, autoHighlight: true, highlightColor: SELECTION, updateTriggers: { getFillColor: sel, getElevation: m } }),
    ]
  }, [sites, selected, showContext, view])

  return (
    <Map
      ref={ref}
      initialViewState={{ bounds: ENGLAND, fitBoundsOptions: { padding: englandPadding() }, pitch: 45 }}
      mapStyle="https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json"
      maxPitch={70}
      onLoad={e => { restyle(e.target); setLoaded(true) }}
      onZoom={e => setView({ zoom: e.viewState.zoom, lat: e.viewState.latitude })}
      attributionControl={{ compact: true }}
      style={{ position: "absolute", inset: 0 }}
    >
      <DeckOverlay
        interleaved={false}
        layers={layers}
        onClick={info => info.object && "verdict" in info.object && onSelect(info.object as Site)}
        getTooltip={({ object }) => object && "verdict" in object ? {
          text: `${titleCase(object.name)} · ${hrs(object)} h\n${VERDICT[verdictOf(object)].label}`,
          style: { background: "#FFFFFF", color: "#0F1B2A", font: "500 13px 'Inter Variable', sans-serif", padding: "6px 10px",
            borderRadius: "6px", border: "1px solid #D9E1E7", boxShadow: "0 4px 12px rgba(15,27,42,.12)" },
        } : null}
      />
      <NavigationControl position="bottom-right" visualizePitch />
      {selected?.gauges.filter(g => g.lat != null).map(g => (
        <Marker key={g.station} longitude={g.lon!} latitude={g.lat!} anchor="top" offset={[0, 10]}>
          <div className="pointer-events-none rounded-md border border-primary/40 bg-background/95 px-2 py-0.5 text-xs whitespace-nowrap shadow-sm">
            <b className="num font-semibold">{fmt(g.mm_0_24h_before + g.mm_24_48h_before, 2)} mm</b>
            <span className="text-muted-foreground"> in 48 h · {g.station}</span>
          </div>
        </Marker>
      ))}
      {selected && (
        <Marker longitude={selected.lon} latitude={selected.lat} anchor="bottom-left" offset={[14, -10]}>
          <div className="pointer-events-none flex gap-2 rounded-md border border-foreground/70 bg-selection px-2.5 py-1 text-sm whitespace-nowrap shadow-sm">
            <b className="font-semibold">{titleCase(selected.name)}</b><span className="num">{hrs(selected)} h</span>
          </div>
        </Marker>
      )}
    </Map>
  )
}
