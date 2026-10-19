import Contacts
import CoreLocation
import MapKit
import XCTest
@testable import SundayDrive

/// The on-device "is this somewhere we cover?" test, and the two search
/// defences built on it: the suggestion filter and the resolve gate.
///
/// The covered area is the 48 contiguous states and DC
/// (`docs/app-goes-national.md`). Every distance quoted below was measured
/// against the Census outline the generated file was built from
/// (`ios/scripts/build_coverage_boundary.py`), not taken on trust. The
/// suggestion strings are verbatim from the iOS 26.4 simulator: the New
/// England ones captured on 2026-10-04 from Boston and from Cupertino, and the
/// national ones as each test says. Tests of the matching rules themselves use
/// constructed strings, built to tell a right rule from a plausible wrong one,
/// and say so.
final class CoverageTests: XCTestCase {

    private func at(_ latitude: Double, _ longitude: Double) -> CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }

    // MARK: - Inside

    func test_the_named_places_are_inside() {
        let places: [(String, CLLocationCoordinate2D)] = [
            ("Boston MA", at(42.3601, -71.0589)),
            ("Washington DC", at(38.8977, -77.0365)),
            ("Cupertino CA", at(37.3349, -122.0090)),
            ("Moab UT", at(38.5733, -109.5498)),
            ("Grand Canyon Village AZ", at(36.0544, -112.1401)),
            ("Furnace Creek CA", at(36.4572, -116.8664)),
            ("Stowe VT", at(44.4654, -72.6874)),
            ("Montauk NY, outside the New England build", at(41.0359, -71.9545)),
            ("The Great Salt Lake, inside Utah's outline", at(41.1, -112.6)),
            ("Lake Okeechobee, inside Florida's", at(26.95, -80.8)),
        ]
        for (name, point) in places {
            XCTAssertTrue(Coverage.contains(point), "\(name) is covered")
        }
    }

    func test_the_islands_with_roads_are_kept() {
        // Simplification is where small islands die. The script keeps every
        // one; these all have roads the server can route on.
        let islands: [(String, CLLocationCoordinate2D)] = [
            ("Key West FL", at(24.5551, -81.7800)),
            ("Big Pine Key FL", at(24.6693, -81.3537)),
            ("Sanibel FL", at(26.4400, -82.0800)),
            ("Galveston TX", at(29.3013, -94.7977)),
            ("Padre Island TX", at(26.9500, -97.3800)),
            ("Dauphin Island AL", at(30.2552, -88.1097)),
            ("Ocracoke NC", at(35.1146, -75.9810)),
            ("Assateague Island MD", at(38.2300, -75.1500)),
            ("Shelter Island NY", at(41.0680, -72.3390)),
            ("Peaks Island ME", at(43.6556, -70.1990)),
            ("Friday Harbor, San Juan Island WA", at(48.5343, -123.0171)),
            ("Eastsound, Orcas Island WA", at(48.6968, -122.9060)),
            ("Bainbridge Island WA", at(47.6262, -122.5212)),
            ("Avalon, Catalina Island CA", at(33.3428, -118.3268)),
            ("Kelleys Island OH", at(41.5962, -82.7110)),
            ("Beaver Island MI, 20 m off the Census shore", at(45.7425, -85.5096)),
        ]
        for (name, point) in islands {
            XCTAssertTrue(Coverage.contains(point), "\(name) is covered")
        }
    }

    func test_the_places_only_reached_through_canada_are_inside() {
        // Covered, and honestly so: they are in a state. Whether the server
        // can route to them without Canadian roads is the server's question
        // (docs/app-goes-national.md, "What the server must change").
        XCTAssertTrue(Coverage.contains(at(48.9860, -123.0680)), "Point Roberts WA")
        XCTAssertTrue(Coverage.contains(at(49.3450, -95.0650)), "Angle Inlet, the Northwest Angle MN")
    }

    func test_border_towns_on_the_us_side_are_inside() {
        // Labelled with their measured distance inside the Census outline.
        let nearBorder: [(String, CLLocationCoordinate2D)] = [
            ("Derby Line VT, 70 m", at(45.0050, -72.0990)),
            ("San Ysidro CA, 90 m from Tijuana", at(32.5430, -117.0300)),
            ("Lubec ME, 150 m", at(44.8606, -66.9842)),
            ("Fort Kent ME, 300 m", at(47.2587, -68.5895)),
            ("Brownsville TX, 330 m from the Rio Grande", at(25.9017, -97.4975)),
            ("Laredo TX, 440 m from the Rio Grande", at(27.5036, -99.5075)),
            ("International Falls MN, 550 m from the Rainy River", at(48.6011, -93.4108)),
            ("Blaine WA, 670 m", at(48.9937, -122.7471)),
            ("Nogales AZ, 860 m", at(31.3404, -110.9343)),
            ("Detroit MI, 920 m from the Detroit River", at(42.3314, -83.0458)),
            ("El Paso TX, 1.05 km from the Rio Grande", at(31.7587, -106.4869)),
            ("Calexico CA, 1.6 km", at(32.6789, -115.4989)),
        ]
        for (name, point) in nearBorder {
            XCTAssertTrue(Coverage.contains(point), name)
        }
    }

    func test_a_fix_just_outside_the_census_line_still_counts() {
        // Both fall *outside* the raw Census outline, which is clipped to a
        // generalised shore and border. This is what the buffer is for.
        XCTAssertTrue(Coverage.contains(at(47.4597, -69.2240)),
                      "Estcourt Station ME, the northern tip, 20 m out")
        XCTAssertTrue(Coverage.contains(at(45.7425, -85.5096)),
                      "Beaver Island MI, 20 m out")
    }

    // MARK: - Outside

    func test_the_named_places_are_outside() {
        let places: [(String, CLLocationCoordinate2D)] = [
            ("Toronto ON, 50 km", at(43.6532, -79.3832)),
            ("Montreal QC, 55 km", at(45.5017, -73.5673)),
            ("Vancouver BC, 31 km", at(49.2827, -123.1207)),
            ("Victoria BC, 19 km", at(48.4284, -123.3656)),
            ("Havana, 158 km", at(23.1136, -82.3666)),
            ("Nassau, 292 km", at(25.0443, -77.3504)),
            ("Hamilton, Bermuda", at(32.2949, -64.7814)),
            ("Paris", at(48.8566, 2.3522)),
            ("Anchorage", at(61.2181, -149.9003)),
            ("Honolulu", at(21.3069, -157.8583)),
            ("San Juan", at(18.4655, -66.1057)),
        ]
        for (name, point) in places {
            XCTAssertFalse(Coverage.contains(point), "\(name) is not covered")
        }
    }

    func test_border_towns_on_the_far_side_are_outside() {
        // Labelled with their measured distance outside the Census outline.
        // The outline reaches at most 793 m from Census land (measured by the
        // script, and printed in the generated file's header).
        let farSide: [(String, CLLocationCoordinate2D)] = [
            ("Fort Frances ON, 570 m over the Rainy River", at(48.6150, -93.3700)),
            ("Windsor ON waterfront, 1.08 km", at(42.3149, -83.0364)),
            ("Niagara Falls ON, 1.16 km", at(43.0896, -79.0849)),
            ("Matamoros TAMPS, 1.32 km", at(25.8690, -97.5027)),
            ("Edmundston NB, 1.46 km over the St. John", at(47.3730, -68.3251)),
            ("Sault Ste. Marie ON, 1.56 km", at(46.5219, -84.3461)),
            ("Nuevo Laredo TAMPS, 2.2 km", at(27.4769, -99.5160)),
            ("Tijuana BC, 3.0 km", at(32.5149, -117.0382)),
            ("Nogales SON, 3.6 km", at(31.3000, -110.9400)),
            ("Ciudad Juárez CHIH, 4.0 km", at(31.7200, -106.4500)),
            ("Mexicali BC, 4.8 km", at(32.6245, -115.4523)),
        ]
        for (name, point) in farSide {
            XCTAssertFalse(Coverage.contains(point), name)
        }
    }

    func test_open_water_is_outside() {
        // Including water no Census state polygon holds: the Great Lakes and
        // the big bays are clipped out of the cartographic file, and the
        // buffer does not close them. A phone on a Lake Michigan ferry is
        // outside, which is true of the roads too.
        let water: [(String, CLLocationCoordinate2D)] = [
            ("The Gulf of Mexico", at(26.0, -90.0)),
            ("The Atlantic off Cape Hatteras", at(35.0, -74.0)),
            ("The Pacific off San Francisco", at(37.7, -123.5)),
            ("Lake Superior", at(47.6, -87.5)),
            ("Lake Michigan", at(43.5, -87.0)),
            ("Chesapeake Bay, 8.8 km from shore", at(38.0, -76.15)),
            ("Puget Sound, 3.4 km from shore", at(47.7, -122.45)),
        ]
        for (name, point) in water {
            XCTAssertFalse(Coverage.contains(point), name)
        }
    }

    func test_a_meaningless_coordinate_is_outside() {
        XCTAssertFalse(Coverage.contains(at(0, 0)), "CoreLocation's junk fix")
        XCTAssertFalse(Coverage.contains(kCLLocationCoordinate2DInvalid))
        XCTAssertFalse(Coverage.contains(at(.nan, .nan)))
    }

    func test_a_rectangle_cannot_stand_in_for_the_outline() {
        // Trap 1 of the national change, as a test: the envelope is a fine
        // search region and a wrong answer to "is this covered?".
        let envelope = MKCoordinateRegion.coverageEnvelope
        func inEnvelope(_ point: CLLocationCoordinate2D) -> Bool {
            abs(point.latitude - envelope.center.latitude) <= envelope.span.latitudeDelta / 2
                && abs(point.longitude - envelope.center.longitude) <= envelope.span.longitudeDelta / 2
        }
        for point in [at(43.6532, -79.3832), at(49.2827, -123.1207), at(32.5149, -117.0382),
                      at(26.0, -90.0), at(25.0443, -77.3504)] {
            XCTAssertTrue(inEnvelope(point), "Toronto, Vancouver, Tijuana, the Gulf and Nassau are in the box")
            XCTAssertFalse(Coverage.contains(point), "and not covered")
        }
    }

    func test_the_envelope_holds_the_whole_outline() {
        let envelope = MKCoordinateRegion.coverageEnvelope
        XCTAssertLessThan(envelope.center.latitude - envelope.span.latitudeDelta / 2,
                          CoverageBoundary.south)
        XCTAssertGreaterThan(envelope.center.latitude + envelope.span.latitudeDelta / 2,
                             CoverageBoundary.north)
        XCTAssertLessThan(envelope.center.longitude - envelope.span.longitudeDelta / 2,
                          CoverageBoundary.west)
        XCTAssertGreaterThan(envelope.center.longitude + envelope.span.longitudeDelta / 2,
                             CoverageBoundary.east)
        // The four corners of the 48: Key West, the Northwest Angle, Cape
        // Flattery and Lubec.
        XCTAssertLessThan(CoverageBoundary.south, 24.5551)
        XCTAssertGreaterThan(CoverageBoundary.north, 49.3450)
        XCTAssertLessThan(CoverageBoundary.west, -124.7144)
        XCTAssertGreaterThan(CoverageBoundary.east, -66.9842)
    }

    func test_the_test_is_cheap() {
        // Every keystroke can call `contains` up to 26 times (`showsSomeOf`),
        // so it has to stay well under a millisecond even in a Debug build.
        // The points sit in the mainland ring's busiest latitudes, where the
        // coasts and the Canadian border all cross. Measured figures are in
        // docs/app-goes-national.md; the bound here is six times looser.
        let points = (0..<2_000).map { i in
            at(41.0 + Double(i % 100) * 0.08, -124.5 + Double(i / 100) * 2.9)
        }
        let start = Date()
        var inside = 0
        for point in points where Coverage.contains(point) { inside += 1 }
        let perCall = Date().timeIntervalSince(start) / Double(points.count)
        XCTAssertGreaterThan(inside, 0)
        XCTAssertLessThan(perCall, 0.000_5, "\(perCall * 1e6) µs a call")
    }

    // MARK: - Suggestions, from captured strings

    func test_suggestions_in_the_48_states_are_kept() {
        // Captured 2026-10-04. The first group was all the New England build
        // kept; the second was all it dropped, and is covered now.
        let kept: [(String, String)] = [
            ("Portland, ME", "United States"),
            ("Portland St", "Boston, MA, United States"),
            ("155 on Portland", "155 Portland St, Boston, MA  02114, United States"),
            ("Portland Head Light", "1000 Shore Rd, Cape Elizabeth, ME  04107, United States"),
            ("Stowe, VT", "United States"),
            ("Mt. Washington State Park",
             "1598 Mt Washington Auto Road, Sargent's Purchase, NH 03589, United States"),
            ("Greenwich Ave", "Warwick, RI, United States"),

            ("Portland, OR", "United States"),
            ("Portland, MI", "United States"),
            ("Concord, CA", "United States"),
            ("Albany, NY", "United States"),
            ("Springfield, MO", "United States"),
            ("Times Square", "1560 Broadway, Unit 1001, New York, NY  10036, United States"),
            ("Times Square–42 Street Station", "New York, NY, United States"),
            ("Mount Washington", "Los Angeles, CA, United States"),
            ("Albany International Airport", "737 NY-155 W, Loudonville, NY  12211, United States"),
            ("Portland International Airport", "7000 NE Airport Way, Portland, OR 97218-1009, United States"),
        ]
        for (title, subtitle) in kept {
            XCTAssertTrue(Coverage.allowsSuggestion(title: title, subtitle: subtitle),
                          "\(title) / \(subtitle)")
        }
    }

    func test_a_suggestion_that_names_no_place_at_all_is_kept() {
        // Two real Boston-area results arrive with nothing after the street.
        // Dropping them would hide good places; `firstInside` checks them.
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Starbucks Coffee Company",
                                                subtitle: "65-66 Beacon St"))
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Omni Mount Washington Resort & Spa",
                                                subtitle: "310 Mount Washington Hotel Road"))
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Somewhere", subtitle: ""))
    }

    func test_a_place_in_canada_is_dropped() {
        // Captured 2026-10-04: by the title, and by the subtitle.
        let dropped: [(String, String)] = [
            ("Burlington, ON", "Canada"),
            ("Sherbrooke, QC", "Canada"),
            ("Edmundston, NB", "Canada"),
            ("Fort Kent, AB", "Canada"),
            ("Sherbrooke", "Montréal QC, Canada"),
            ("Université de Sherbrooke", "2500 Boul de l'Université, Sherbrooke QC J1K 2R1, Canada"),
            ("Sherbrooke", "St. Mary's, NS, Canada"),
            ("Edmundston Airport", "30 ch. de l'Aéroport, Saint-Jacques DSL NB E7B 2Z6, Canada"),
            ("Lubec Narrows", "Campobello Island, NB, Canada"),
        ]
        for (title, subtitle) in dropped {
            XCTAssertFalse(Coverage.allowsSuggestion(title: title, subtitle: subtitle),
                           "\(title) / \(subtitle)")
        }
    }

    func test_a_us_place_outside_the_48_is_dropped() {
        // Constructed, in the two shapes the captured strings take: the code
        // at the end of the title, and before the ZIP in the subtitle. A
        // filter that kept every US address would let these through.
        let dropped: [(String, String)] = [
            ("Anchorage, AK", "United States"),
            ("Hilo, HI", "United States"),
            ("Kalakaua Ave", "Honolulu, HI  96815, United States"),
            ("Ponce, PR", "United States"),
        ]
        for (title, subtitle) in dropped {
            XCTAssertFalse(Coverage.allowsSuggestion(title: title, subtitle: subtitle),
                           "\(title) / \(subtitle)")
        }
    }

    func test_a_place_abroad_is_dropped_by_its_country() {
        // Captured 2026-10-04. No state code anywhere, so the subtitle's last
        // part decides. England is not a country name ISO knows; Apple writes
        // it anyway.
        let dropped: [(String, String)] = [
            ("Paris", "France"),
            ("Lubec", "33980 Audenge, France"),
            ("Manchester", "England"),
            ("Greenwich", "London, England"),
            ("Lübeck", "Schleswig-Holstein, Germany"),
            ("Times Square", "Andheri East, Mumbai, Maharashtra, India"),
            ("Sherbrooke, VIC", "Australia"),
        ]
        for (title, subtitle) in dropped {
            XCTAssertFalse(Coverage.allowsSuggestion(title: title, subtitle: subtitle),
                           "\(title) / \(subtitle)")
        }
    }

    func test_national_captures_are_judged_right() {
        // Captured 2026-10-18 on the iOS 26.4 simulator, the completer ranked
        // around San Diego and around Detroit, the two cities on the borders.
        let kept: [(String, String)] = [
            ("Moab, UT", "United States"),
            ("Moab Airport", "110 W Aviation Way, Moab, UT 84532, United States"),
            ("Portland, TX", "United States"),
            ("Toronto, OH", "United States"),
            ("Anchorage, KY", "United States"),
            ("Windsor, CO", "United States"),
            ("San Juan, TX", "United States"),
            ("Ensenada, NM", "United States"),
            ("Tijuana River Valley", "San Diego, CA, United States"),
            ("Niagara Falls State Park", "332 Prospect St, Niagara Falls, NY 14303, United States"),
            ("Hidden Anchorage", "CA, United States"),
        ]
        for (title, subtitle) in kept {
            XCTAssertTrue(Coverage.allowsSuggestion(title: title, subtitle: subtitle),
                          "\(title) / \(subtitle)")
        }
        let dropped: [(String, String)] = [
            ("Tijuana", "B.C., Mexico"),
            ("Playas de Tijuana", "Privada Paseo Costero, Tijuana, BC, Mexico"),
            ("Tijuana International Airport",
             "Carretera Aeropuerto S/N, Col. Nueva Tijuana, Mesa de Otay, 22435 Tijuana, BC, Mexico"),
            ("Ciudad Juárez", "Chih., Mexico"),
            ("Ensenada", "B.C., Mexico"),
            ("Toronto, ON", "Canada"),
            ("Toronto Island", "Ontario, Canada"),
            ("Toronto Pearson International Airport", "6301 Silver Dart Dr, Mississauga ON  L5P 1B2, Canada"),
            ("Windsor, ON", "Canada"),
            ("Victoria Tavern", "400 Chilver Rd, Windsor ON N8Y 2J7, Canada"),
            ("Clifton Hill - Niagara Falls Fun", "4960 Clifton Hill, Niagara Falls ON L2G 3N4, Canada"),
            ("Victoria, BC", "Canada"),
            ("Anchorage, AK", "United States"),
            ("Anchorage Cove", "AK, United States"),
            ("Honolulu, HI", "United States"),
            ("Honolulu Zoo", "151 Kapahulu Ave, Honolulu, HI 96815, United States"),
            ("San Juan", "PR, United States"),
            ("San Juan", "Dominican Republic"),
            // The two the New England rules let through: a state's name and
            // no code, and a country in the title over an empty subtitle.
            ("Honolulu", "Kona, Hawaiʻi"),
            ("Honolulu", "Puna, Hawaiʻi"),
            ("San Juan, Argentina", ""),
        ]
        for (title, subtitle) in dropped {
            XCTAssertFalse(Coverage.allowsSuggestion(title: title, subtitle: subtitle),
                           "\(title) / \(subtitle)")
        }
    }

    func test_a_bare_street_address_is_left_to_the_resolve_gate() {
        // Captured 2026-10-18. Both are outside coverage, and both name only
        // a street: the filter cannot tell, so they are shown, and
        // `firstInside` refuses them by coordinate and state.
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Anchorage International Airport",
                                                subtitle: "5000 W International Airport Rd"))
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Windsor Detroit Tunnel",
                                                subtitle: "555 Goyeau St"))
    }

    func test_codes_are_matched_as_words_not_letters() {
        // Constructed. "ON" inside a word is not Ontario, and "NE" in front
        // of a street name is a direction. A substring match would decide
        // these on the wrong letters.
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Café", subtitle: "100 NE Main St"))
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Lemon St", subtitle: "12 LEMON ST"))
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Akron", subtitle: "AKRON, OH"))
        XCTAssertFalse(Coverage.allowsSuggestion(title: "Honda", subtitle: "HONDA DR, Toronto, ON M1B 2X5"))
    }

    func test_the_last_code_in_an_address_is_the_one_that_counts() {
        // Constructed. A route number before the state: the state wins, in
        // either direction.
        XCTAssertTrue(Coverage.allowsSuggestion(title: "Gas", subtitle: "ON 3, Windsor Ave, Detroit, MI 48226"))
        XCTAssertFalse(Coverage.allowsSuggestion(title: "Gas", subtitle: "MI 3, Ouellette Ave, Windsor, ON N9A 1A1"))
    }

    // MARK: - The resolve gate

    func test_a_covered_result_is_accepted() {
        XCTAssertTrue(Coverage.accepts(at(43.6590, -70.2569), administrativeArea: "ME"), "Portland ME")
        XCTAssertTrue(Coverage.accepts(at(45.5151, -122.6795), administrativeArea: "OR"), "Portland OR")
        XCTAssertTrue(Coverage.accepts(at(38.5733, -109.5498), administrativeArea: "UT"), "Moab")
        XCTAssertTrue(Coverage.accepts(at(38.8977, -77.0365), administrativeArea: "DC"), "Washington")
        XCTAssertTrue(Coverage.accepts(at(38.8977, -77.0365), administrativeArea: "District of Columbia"))
        XCTAssertTrue(Coverage.accepts(at(42.3625, -71.0876), administrativeArea: nil), "no state named")
        XCTAssertTrue(Coverage.accepts(at(42.3625, -71.0876), administrativeArea: ""))
        XCTAssertTrue(Coverage.accepts(at(42.3625, -71.0876), administrativeArea: "Massachusetts"))
        XCTAssertTrue(Coverage.accepts(at(42.3625, -71.0876), administrativeArea: "ma"))
    }

    func test_a_result_elsewhere_is_refused() {
        XCTAssertFalse(Coverage.accepts(at(43.6532, -79.3832), administrativeArea: "ON"), "Toronto")
        XCTAssertFalse(Coverage.accepts(at(32.5149, -117.0382), administrativeArea: "B.C."), "Tijuana")
        XCTAssertFalse(Coverage.accepts(at(61.2181, -149.9003), administrativeArea: "AK"), "Anchorage")
        XCTAssertFalse(Coverage.accepts(at(48.8568, 2.3511), administrativeArea: "Île-de-France"), "Paris")
    }

    func test_a_place_over_the_line_is_refused_by_its_state() {
        // Inside the buffered outline, measured at 370 m and 80 m over the
        // Census line. Their states are what keep them out.
        let stanstead = at(45.0090, -72.0970)
        XCTAssertTrue(Coverage.contains(stanstead), "precondition: the buffer reaches Stanstead")
        XCTAssertFalse(Coverage.accepts(stanstead, administrativeArea: "QC"))

        let fortFrances = at(48.6089, -93.4030)
        XCTAssertTrue(Coverage.contains(fortFrances), "precondition: the buffer reaches Fort Frances")
        XCTAssertFalse(Coverage.accepts(fortFrances, administrativeArea: "ON"))
        XCTAssertFalse(Coverage.accepts(fortFrances, administrativeArea: "Ontario"))
    }

    private func item(_ point: CLLocationCoordinate2D, state: String) -> MKMapItem {
        let address = CNMutablePostalAddress()
        address.state = state
        return MKMapItem(placemark: MKPlacemark(coordinate: point, postalAddress: address))
    }

    func test_the_first_covered_result_wins_not_the_first_result() {
        let london = item(at(42.9849, -81.2453), state: "ON")
        let londonKY = item(at(37.1290, -84.0833), state: "KY")
        XCTAssertEqual(london.placemark.administrativeArea, "ON", "precondition: the fixture carries a state")

        let chosen = Coverage.firstInside([london, londonKY])
        XCTAssertEqual(chosen?.placemark.administrativeArea, "KY")
        XCTAssertNil(Coverage.firstInside([london]), "never an uncovered item")
        XCTAssertNil(Coverage.firstInside([]))
    }

    func test_the_refusal_names_the_place_and_the_area() {
        XCTAssertEqual(Coverage.notCovered("Toronto"),
                       "“Toronto” is outside the area Sunday Drive covers: "
                       + "the 48 contiguous states and Washington, DC.")
    }

    // MARK: - The search bias

    func test_a_bias_inside_the_area_is_left_alone() {
        // Ranking near the user is what keeps "main street" local.
        let moab = MKCoordinateRegion.around(at(38.5733, -109.5498))
        let bias = Coverage.searchBias(around: moab)
        XCTAssertFalse(bias.restricted, "required on 30 km, Denver from Moab would find nothing")
        XCTAssertEqual(bias.region.center.latitude, moab.center.latitude, accuracy: 1e-9)
        XCTAssertEqual(bias.region.span.latitudeDelta, moab.span.latitudeDelta, accuracy: 1e-9)
    }

    func test_a_bias_centred_off_the_coast_that_shows_covered_land_is_kept() {
        // The New England rule judged the centre alone, and would have ranked
        // a search from the Florida Keys from Kansas.
        let offKeyWest = MKCoordinateRegion.around(at(24.47, -81.80))
        XCTAssertFalse(Coverage.contains(offKeyWest.center), "precondition: the centre is at sea")
        XCTAssertFalse(Coverage.searchBias(around: offKeyWest).restricted)

        let windsor = MKCoordinateRegion.around(at(42.3000, -83.0200))
        XCTAssertFalse(Coverage.contains(windsor.center), "precondition: the centre is in Ontario")
        XCTAssertFalse(Coverage.searchBias(around: windsor).restricted, "Detroit is on the map")
    }

    func test_a_bias_that_shows_none_of_the_area_becomes_the_envelope() {
        let envelope = MKCoordinateRegion.coverageEnvelope
        for region in [MKCoordinateRegion.around(at(43.6532, -79.3832)),   // Toronto
                       MKCoordinateRegion.around(at(26.0, -90.0)),         // the Gulf of Mexico
                       MKCoordinateRegion.around(at(48.8566, 2.3522))] {   // Paris
            let bias = Coverage.searchBias(around: region)
            XCTAssertTrue(bias.restricted)
            XCTAssertEqual(bias.region.center.latitude, envelope.center.latitude, accuracy: 1e-9)
            XCTAssertEqual(bias.region.span.longitudeDelta, envelope.span.longitudeDelta, accuracy: 1e-9)
        }
    }

    func test_a_bias_wider_than_the_area_becomes_the_envelope() {
        // The opening camera, widened to a card's shape. Its centre is in
        // Kansas, so only the width decides this.
        let wide = MKCoordinateRegion(center: MKCoordinateRegion.coverage.center,
                                      span: MKCoordinateSpan(latitudeDelta: 40, longitudeDelta: 70))
        XCTAssertTrue(Coverage.contains(wide.center), "precondition: the centre is inside")
        XCTAssertTrue(Coverage.searchBias(around: wide).restricted)
    }

    func test_the_home_region_ranks_around_the_phone() {
        let home = MKCoordinateRegion.home(around: at(38.5733, -109.5498))
        let bias = Coverage.searchBias(around: home)
        XCTAssertFalse(bias.restricted)
        XCTAssertEqual(bias.region.center.latitude, 38.5733, accuracy: 1e-9)
    }
}
