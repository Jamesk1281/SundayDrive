import SwiftUI

/// Who the app owes credit to, and in the words their licences ask for.
///
/// Sunday Drive draws OpenStreetMap-derived road geometry on the map, names OSM
/// streets in its maneuvers and speaks them aloud, and every score it shows is
/// built from two more open datasets. All three require attribution in the
/// thing that reaches the user — a private repo's README discharges nothing.
///
/// The strings live here, not inline in the view, for one reason: they are the
/// obligation. `AttributionTests` asserts each one is present and reachable, so
/// a later refactor that drops a line fails a test instead of quietly shipping
/// an app that is out of compliance.
///
/// **Reproduced, not paraphrased.** Each `credit` below is the wording the
/// licensor publishes, checked against the source on 2026-08-31 (URLs in each
/// entry). Do not "tidy" them — the capitalisation, the `©`, the en dash in
/// "Open Government Licence – Canada" and the trailing punctuation are all part
/// of text somebody else wrote.
struct DataSource: Identifiable {
    /// What this source gives the app, in the user's terms — not the dataset's
    /// name. Someone reading a credits screen wants to know what they are
    /// looking at before they are told who made it.
    let role: String
    /// The dataset, as its publisher names it.
    let name: String
    /// The credit lines, verbatim. More than one where the source is an
    /// aggregate and several of its upstreams reach this app's footprint.
    let credit: [String]
    /// The licence, named the way the licensor names it. `nil` where the source
    /// renders its own attribution and imposes no string on us (Apple).
    let licence: String?
    /// Where the licence and the data's own provenance can be read. Required by
    /// the ODbL guideline for OSM ("There needs to be a way to access more
    /// information, including origin and licence of the data"), and good
    /// practice for the rest.
    let url: URL

    var id: String { name }
}

enum DataSources {

    /// The one line that has to be on screen without the user doing anything.
    ///
    /// The OSMF attribution guideline's base requirement is that attribution
    /// "must be presented to anyone who uses, views, accesses, interacts with,
    /// or is otherwise exposed to the map or produced work", and that the
    /// format "should not require individuals to interact with the map or
    /// produced work to see the attribution". A credits screen one tap away is
    /// the safe harbour for attribution that was *shown and then collapsed* —
    /// on its own it is not the safe harbour for never showing it at all. So
    /// this sits visible in the planning sheet at every detent, and taps
    /// through to the full list.
    ///
    /// "Map data from" rather than a bare copyright line because the guideline
    /// invites exactly that qualification when the reuser has rendered the data
    /// to their own design, which is what the route lines are: "OSM does not
    /// wish to claim credit for data or other material that did not come from
    /// it, so feel free to qualify the credit to explain what OSM content you
    /// are using." The basemap under those lines is Apple's, so the
    /// qualification is not decoration — an unqualified "© OpenStreetMap
    /// contributors" over an Apple basemap would credit OSM for Apple's work.
    static let shortCredit = "Map data from OpenStreetMap"

    /// The link that `shortCredit` has to reach, per the guideline's "This may
    /// be done by making the text 'OpenStreetMap' a link to
    /// openstreetmap.org/copyright".
    static let openStreetMapCopyrightURL = URL(string: "https://www.openstreetmap.org/copyright")!

    static let all: [DataSource] = [openStreetMap, worldCover, terrainTiles, appleMaps]

    /// The route-guidance notice, **verbatim and non-negotiable**.
    ///
    /// Apple Developer Program License Agreement §3.3.3(F)(iii) — "Data and
    /// Privacy" → F. "Location and Maps; User Consents" → (iii): "For
    /// Applications that use location-based APIs for real-time navigation
    /// (including, but not limited to, turn-by-turn route guidance and other
    /// routing that is enabled through the use of a sensor), You must have an
    /// end user license agreement that includes the following notice: ..." —
    /// and this string is that notice.
    /// `NavigationModel` drives turn-by-turn guidance from `CoreLocation` fixes
    /// and `VoiceGuide` speaks them, so the clause applies squarely.
    ///
    /// **Do not reword, sentence-case, or soften this.** It is a fixed string in
    /// a contract, capitals included.
    ///
    /// **Rendered in exactly one place: `BeforeYouDriveView`,** which is shown
    /// once at first launch and is permanently reachable from the Sources
    /// screen. It used to sit at the bottom of the credits sheet, which is
    /// compliant and read by nobody. Two ways in, one view, one copy — do not
    /// add a second.
    ///
    /// Showing it in the app does **not** by itself discharge §3.3.3(F)(iii),
    /// which asks for an *end user licence agreement*: a custom EULA carrying this
    /// text still has to be filed in App Store Connect before submission
    /// (Apple's default Licensed Application EULA does not contain it). The
    /// text to paste is in `docs/app-store-submission.md`. It is in the app as
    /// well because the person it protects is driving, and a clause filed on a
    /// website they never read protects nobody. See
    /// `docs/legal-and-ip-audit.md`.
    ///
    /// It is also true on the merits: this app deliberately routes drivers onto
    /// small rural roads, and `via`-way turn restrictions and lane guidance are
    /// both listed unimplemented in the README.
    static let routeGuidanceNotice =
        "YOUR USE OF THIS REAL TIME ROUTE GUIDANCE APPLICATION IS AT YOUR SOLE "
        + "RISK. LOCATION DATA MAY NOT BE ACCURATE."

    /// OpenStreetMap — every road, street name and turn restriction, via the
    /// Geofabrik extracts the pipeline consumes.
    ///
    /// The routes drawn on screen are a **Produced Work** under ODbL §4.3:
    /// attribution is required, share-alike is not. (The derived `.parquet`
    /// graph in `data/processed` is a different thing — a Derivative Database,
    /// §4.4 — and distributing *that* would trigger share-alike. It never
    /// leaves the author's own machines today. See
    /// `docs/licensing-and-attribution-brief.md` before building any
    /// download-a-region-for-offline-use feature.)
    ///
    /// Both credit lines are acceptable forms per the guideline: "Attribution
    /// must be to 'OpenStreetMap'" and "The historical forms of attribution
    /// '© OpenStreetMap contributors' or '© OpenStreetMap' are acceptable."
    /// Checked against <https://osmfoundation.org/wiki/Licence/Attribution_Guidelines>
    /// (adopted 2021-06-25) and <https://www.openstreetmap.org/copyright>.
    static let openStreetMap = DataSource(
        role: "Roads, street names and routing",
        name: "OpenStreetMap",
        // Geofabrik's own provenance line, from <https://download.geofabrik.de/>:
        // "Data processed by Geofabrik GmbH and created by OpenStreetMap
        // Contributors". Their extract is plausibly itself a Derivative Database
        // under ODbL, which would make Geofabrik a database author owed
        // attribution under §4.3 — and it is simply accurate about where the
        // bytes came from. Cheap, so credited.
        credit: ["© OpenStreetMap contributors",
                 "Extracts processed by Geofabrik GmbH"],
        licence: "Open Database License (ODbL) 1.0",
        url: openStreetMapCopyrightURL
    )

    /// ESA WorldCover v200 (2021) — half of `c_forest` at `pipeline/score.py`,
    /// and forest carries 0.18 of the 1.14 of total scenery weight, so this is
    /// in every score the app displays.
    ///
    /// Credit is ESA's own prescribed CC-BY line for **v200/2021** specifically
    /// — the consortium words it per version and this is the version
    /// `pipeline/landcover.py` fetches. Checked against
    /// <https://esa-worldcover.org/en/data-access>.
    static let worldCover = DataSource(
        role: "Forest and green cover in the scenery scores",
        name: "ESA WorldCover 10 m 2021 v200",
        credit: ["© ESA WorldCover project 2021 / Contains modified Copernicus "
                 + "Sentinel data (2021) processed by ESA WorldCover consortium"],
        licence: "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        url: URL(string: "https://esa-worldcover.org")!
    )

    /// The AWS Terrain Tiles (Terrarium) set — feeds `c_relief`.
    ///
    /// **This is an aggregate, not a dataset.** It is a mosaic of many national
    /// elevation products, each with its own attribution, and it would be wrong
    /// to call it public domain because its largest US upstream is. The AWS Open
    /// Data registry entry names its licence as
    /// <https://github.com/tilezen/joerd/blob/master/docs/attribution.md>, whose
    /// "Required attribution" block lists a line per upstream; the three below
    /// are reproduced from it verbatim.
    ///
    /// Which three: `joerd`'s own per-zoom source table says that at **zoom 11**
    /// — the zoom `pipeline/elevation.py` fetches — land is `NED/3DEP` and
    /// `SRTM`, plus `NRCAN` in Canada, and ocean is `ETOPO1`. The pipeline's
    /// `BBOX` is `(-73.76, 40.93, -66.87, 47.47)`, which reaches north of the
    /// Maine border into Quebec and New Brunswick and out over the Gulf of
    /// Maine, so all three upstreams are inside the footprint the relief raster
    /// is built from. `ArcticDEM` and `GMTED` only apply above 60° latitude at
    /// this zoom and the European, Austrian, Australian, Mexican, UK, Norwegian
    /// and New Zealand lines are elsewhere entirely, so they are not reproduced.
    ///
    /// Note the Canadian line is the reason not to shortcut this: it is the
    /// Open Government Licence – Canada, not US-government public domain.
    static let terrainTiles = DataSource(
        role: "Hills and valleys in the scenery scores",
        name: "Terrain Tiles (AWS Open Data, formerly Mapzen)",
        credit: [
            "United States 3DEP (formerly NED) and global GMTED2010 and SRTM "
                + "terrain data courtesy of the U.S. Geological Survey.",
            "Global ETOPO1 terrain data U.S. National Oceanic and Atmospheric "
                + "Administration",
            "Canada terrain data contains information licensed under the Open "
                + "Government Licence – Canada;",
        ],
        licence: nil,
        url: URL(string: "https://registry.opendata.aws/terrain-tiles/")!
    )

    /// The basemap under the route lines. MapKit draws Apple's own attribution
    /// and legal link itself, so no string is owed here — it is listed so the
    /// screen answers "and the map itself?" rather than leaving the user to
    /// assume the roads and the basemap came from the same place.
    static let appleMaps = DataSource(
        role: "The underlying map",
        name: "Apple Maps",
        credit: ["Basemap and place search © Apple Inc. and its data providers, "
                 + "credited on the map itself."],
        licence: nil,
        url: URL(string: "https://www.apple.com/legal/internet-services/maps/")!
    )
}

/// **Sources** — what the app is built from, and the credit each of those
/// licences asks for.
///
/// Every credit string below is reproduced verbatim from
/// `DataSources`; none of them changed in the redesign, because they are
/// somebody else's text. What changed is that the sentence explaining *why*
/// anyone is reading this is now the largest thing on the screen rather than
/// the smallest, and each source carries the colour of the thing it produces —
/// the same six hues as the route breakdown and the *What you like* sheet.
///
/// The safety notice is no longer on this screen. It has its own,
/// `BeforeYouDriveView`, reached from the row at the bottom — one copy, two
/// ways in.
struct AboutView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var showingNotice = false
    /// The one appearance control. The app is dark by default — see
    /// `ContentView` for why, and for the one hour of the day that argues the
    /// other way.
    @AppStorage("matchSystemAppearance") private var matchSystem = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    Text("The roads on this map, and the scores they are rated with, "
                         + "come from open data. These are the people who made it.")
                        .font(.system(size: 18, weight: .semibold))
                        .foregroundStyle(Color.ink)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.bottom, 14)

                    ForEach(DataSources.all) { source in
                        entry(for: source)
                    }

                    Toggle(isOn: $matchSystem) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Match system appearance")
                                .font(.system(size: 15.5, weight: .semibold))
                                .foregroundStyle(Color.ink)
                            Text("Off, the app stays dark — easier to read from a "
                                 + "windscreen mount at the ends of the day.")
                                .font(.system(size: 12))
                                .foregroundStyle(Color.ink2)
                        }
                    }
                    .tint(Color.amber)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(Color.sunk, in: RoundedRectangle(cornerRadius: 15))
                    .padding(.top, 18)

                    Button { showingNotice = true } label: {
                        HStack {
                            Text("Before you drive")
                                .font(.system(size: 15.5, weight: .semibold))
                                .foregroundStyle(Color.ink)
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundStyle(Color.ink3)
                        }
                        .padding(.horizontal, 16)
                        .frame(height: 50)
                        .background(Color.sunk, in: RoundedRectangle(cornerRadius: 15))
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .padding(.top, 10)
                }
                .padding(Metric.margin)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color.paper)
            .navigationTitle("Sources")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }.tint(Color.amberText)
                }
            }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
        .sheet(isPresented: $showingNotice) { BeforeYouDriveView() }
    }

    /// One source: what it gives us, its verbatim credit, its licence, and a
    /// link out to the licence and the data's own provenance.
    private func entry(for source: DataSource) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 7) {
                RoundedRectangle(cornerRadius: 3)
                    .fill(Self.hue(for: source))
                    .frame(width: 9, height: 9)
                Text(source.role).sectionLabel()
            }
            Text(source.name)
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(Color.ink)

            // The credit lines themselves. Selectable so the wording can be
            // copied out exactly — it is somebody else's text and a user (or an
            // App Review reader) may want it character for character.
            ForEach(Array(source.credit.enumerated()), id: \.offset) { _, line in
                Text(line)
                    .font(.system(size: 12.5))
                    .foregroundStyle(Color.ink)
                    .textSelection(.enabled)
            }

            if let licence = source.licence {
                Text(licence)
                    .font(.system(size: 12))
                    .foregroundStyle(Color.ink2)
            }

            Link(destination: source.url) {
                Text(Self.linkLabel(source.url))
                    .font(.system(size: 12))
                    .foregroundStyle(Color.amberText)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 12)
        .overlay(alignment: .bottom) { Divider().overlay(Color.hairline) }
    }

    /// The colour of the thing this source produces, where it produces one the
    /// breakdown names. Apple and OSM get slate: they are the map and the
    /// roads, not a scenery component.
    private static func hue(for source: DataSource) -> Color {
        if source.name.contains("WorldCover") { return BeautyType.hue(for: "forest") }
        if source.name.contains("Terrain")    { return BeautyType.hue(for: "hills") }
        return .slate
    }

    /// A link's visible text: host **and path**, scheme and `www.` dropped.
    ///
    /// The host alone would read "openstreetmap.org" on a link that goes to
    /// openstreetmap.org/copyright — and /copyright is the specific page the
    /// OSMF guideline names as what the credit has to reach. Showing the path
    /// is the difference between a link that says where it goes and one that
    /// quietly says something else.
    static func linkLabel(_ url: URL) -> String {
        var text = url.absoluteString
        for prefix in ["https://", "http://", "www."] where text.hasPrefix(prefix) {
            text.removeFirst(prefix.count)
        }
        if text.hasSuffix("/") { text.removeLast() }
        return text
    }
}
