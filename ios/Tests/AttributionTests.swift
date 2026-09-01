import XCTest
@testable import Scenic

/// The attribution the app owes its data sources.
///
/// These are not tests of behaviour — they are tests of *strings*, which is
/// unusual and is the point. Every line asserted here is wording somebody else
/// published as the condition of using their data, and the failure mode this
/// guards against is not a crash: it is a refactor that tidies a credit into
/// something nobody licensed, or drops a source, and ships an app that is out of
/// compliance while every other test stays green.
///
/// Sources checked 2026-08-31:
///   • <https://osmfoundation.org/wiki/Licence/Attribution_Guidelines> (adopted 2021-06-25)
///   • <https://www.openstreetmap.org/copyright>
///   • <https://esa-worldcover.org/en/data-access>
///   • <https://github.com/tilezen/joerd/blob/master/docs/attribution.md>, which is
///     the document the AWS Open Data registry entry for Terrain Tiles names as
///     its licence.
final class AttributionTests: XCTestCase {

    // MARK: - The credit that has to be on screen unprompted

    /// The guideline: "Attribution must be to 'OpenStreetMap'." The visible line
    /// is the one that has to satisfy it, because the sheet behind it is a tap
    /// away and taps are the thing the base requirement says not to depend on.
    func test_the_always_visible_credit_names_openstreetmap() {
        XCTAssertTrue(DataSources.shortCredit.contains("OpenStreetMap"),
                      "The visible credit is the app's only unprompted attribution; "
                      + "it has to name OpenStreetMap. Got: \(DataSources.shortCredit)")
    }

    /// It is qualified rather than a bare copyright line because the basemap
    /// under the route lines is Apple's, and the guideline asks reusers not to
    /// claim OSM credit for material that did not come from OSM.
    func test_the_visible_credit_says_it_is_the_data_that_came_from_osm() {
        XCTAssertEqual(DataSources.shortCredit, "Map data from OpenStreetMap")
    }

    /// "This may be done by making the text 'OpenStreetMap' a link to
    /// openstreetmap.org/copyright" — so that URL specifically, not the OSM
    /// home page, has to be what the credit reaches.
    func test_the_credit_reaches_the_osm_copyright_page() {
        XCTAssertEqual(DataSources.openStreetMapCopyrightURL.absoluteString,
                       "https://www.openstreetmap.org/copyright")
        XCTAssertEqual(DataSources.openStreetMap.url,
                       DataSources.openStreetMapCopyrightURL)
    }

    // MARK: - The verbatim credits

    /// Both acceptable forms per the guideline; this is the one the app uses.
    func test_openstreetmap_is_credited_in_an_accepted_form() {
        XCTAssertTrue(DataSources.openStreetMap.credit.contains("© OpenStreetMap contributors"))
    }

    /// "Attribution must also make it clear that the data is available under the
    /// Open Database License." Naming it, not just linking it.
    func test_the_odbl_is_named() {
        let licence = DataSources.openStreetMap.licence ?? ""
        XCTAssertTrue(licence.contains("Open Database License"), "Got: \(licence)")
        XCTAssertTrue(licence.contains("ODbL"), "Got: \(licence)")
    }

    /// ESA's prescribed CC-BY line for v200/2021 — the version
    /// `pipeline/landcover.py` fetches. The consortium words this per version,
    /// so the year appearing twice is not a typo to be deduplicated.
    func test_esa_worldcover_carries_esas_own_prescribed_line() {
        XCTAssertEqual(
            DataSources.worldCover.credit,
            ["© ESA WorldCover project 2021 / Contains modified Copernicus "
             + "Sentinel data (2021) processed by ESA WorldCover consortium"])
        XCTAssertTrue(DataSources.worldCover.licence?.contains("CC BY 4.0") == true)
    }

    /// The three `joerd` lines whose upstreams reach the footprint
    /// `pipeline/elevation.py` builds its relief raster over, at the zoom it
    /// builds it at. Reproduced from the required-attribution block, not
    /// paraphrased.
    func test_the_terrain_tile_upstreams_are_each_credited() {
        let credit = DataSources.terrainTiles.credit
        XCTAssertEqual(credit.count, 3, "Got: \(credit)")

        XCTAssertTrue(credit.contains { $0.contains("3DEP (formerly NED)")
            && $0.contains("U.S. Geological Survey") },
            "USGS covers 3DEP and SRTM, which are the land sources at zoom 11 "
            + "over New England. Got: \(credit)")

        XCTAssertTrue(credit.contains { $0.contains("ETOPO1")
            && $0.contains("National Oceanic and Atmospheric Administration") },
            "ETOPO1 is the ocean source at every zoom, and the BBOX reaches out "
            + "over the Gulf of Maine. Got: \(credit)")

        // The one that makes the "it's all US public domain" shortcut wrong.
        // BBOX's northern edge is 47.47, which is inside Quebec and New
        // Brunswick, and at zoom 11 Canadian land is NRCAN's CDEM.
        XCTAssertTrue(credit.contains { $0.contains("Open Government Licence – Canada") },
            "The BBOX crosses the Canadian border, so CDEM is in the mosaic and "
            + "its licence is not US-government public domain. Got: \(credit)")
    }

    /// The trap this whole entry exists to avoid.
    ///
    /// `elevation-tiles-prod` is an *aggregate* of many national elevation
    /// products. Its largest US upstream (3DEP) is public domain, and the
    /// tempting shortcut is to conclude the tile set is — which is false, and
    /// would be a claim the app made about somebody else's licence. Nothing here
    /// may assert it.
    func test_the_terrain_aggregate_is_never_called_public_domain() {
        for source in DataSources.all {
            for line in source.credit {
                XCTAssertFalse(line.lowercased().contains("public domain"),
                               "\(source.name) asserts a public-domain claim: \(line)")
            }
            XCTAssertFalse(source.licence?.lowercased().contains("public domain") == true,
                           "\(source.name) asserts a public-domain licence: \(source.licence ?? "")")
        }
    }

    // MARK: - Nothing is silently missing

    /// Each of the three datasets the app is actually built from has to be in
    /// the list the screen renders — an entry that exists but is not in `all` is
    /// attribution that reaches nobody.
    func test_every_source_the_app_uses_is_on_the_screen() {
        let names = DataSources.all.map(\.name)
        XCTAssertTrue(names.contains("OpenStreetMap"), "Got: \(names)")
        XCTAssertTrue(names.contains { $0.contains("WorldCover") }, "Got: \(names)")
        XCTAssertTrue(names.contains { $0.contains("Terrain Tiles") }, "Got: \(names)")
    }

    /// Every entry needs somewhere to read the licence and the data's own
    /// provenance — the guideline's "There needs to be a way to access more
    /// information, including origin and licence of the data".
    func test_every_source_links_somewhere_reachable() {
        for source in DataSources.all {
            XCTAssertEqual(source.url.scheme, "https",
                           "\(source.name) must link over https, got \(source.url)")
            XCTAssertNotNil(source.url.host, "\(source.name) has no host: \(source.url)")
        }
    }

    /// A link's visible text must keep the path, not collapse to the host.
    ///
    /// The guideline names openstreetmap.org/**copyright** as the page the
    /// credit has to reach. Rendering only the host would put "openstreetmap.org"
    /// on screen under a link that goes somewhere more specific — a link that
    /// says something other than where it goes.
    func test_a_link_shows_where_it_actually_goes() {
        XCTAssertEqual(AboutView.linkLabel(DataSources.openStreetMapCopyrightURL),
                       "openstreetmap.org/copyright")
        XCTAssertEqual(AboutView.linkLabel(URL(string: "https://esa-worldcover.org")!),
                       "esa-worldcover.org")
        XCTAssertEqual(
            AboutView.linkLabel(URL(string: "https://registry.opendata.aws/terrain-tiles/")!),
            "registry.opendata.aws/terrain-tiles")
    }

    /// No entry may be blank. A credits screen with an empty row is worse than
    /// one without the row: it looks discharged and is not.
    func test_no_entry_is_empty() {
        for source in DataSources.all {
            XCTAssertFalse(source.role.isEmpty, "\(source.name) has no role")
            XCTAssertFalse(source.name.isEmpty, "an entry has no name")
            XCTAssertFalse(source.credit.isEmpty, "\(source.name) has no credit lines")
            for line in source.credit {
                XCTAssertFalse(line.trimmingCharacters(in: .whitespaces).isEmpty,
                               "\(source.name) has a blank credit line")
            }
        }
    }
}
