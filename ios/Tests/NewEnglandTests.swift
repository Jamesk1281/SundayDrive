import Contacts
import CoreLocation
import MapKit
import XCTest
@testable import SundayDrive

/// The on-device "is this in New England?" test, and the two search defences
/// built on it: the suggestion filter and the resolve gate.
///
/// Every distance quoted below was measured against the Census outline the
/// generated file was built from (`tools/build_new_england_boundary.py`), not
/// taken on trust. The suggestion strings in the kept and dropped lists are
/// verbatim from the iOS 26.4 simulator, captured on 2026-10-04 from Boston
/// and from Cupertino: the brief warned against imagined strings, and the real
/// ones put a city's state in the *title*, which no imagined fixture did. The
/// two tests of the matching rules themselves use constructed strings, built
/// to tell a right rule from a plausible wrong one.
final class NewEnglandTests: XCTestCase {

    private func at(_ latitude: Double, _ longitude: Double) -> CLLocationCoordinate2D {
        CLLocationCoordinate2D(latitude: latitude, longitude: longitude)
    }

    // MARK: - Inside

    func test_the_named_places_are_inside() {
        let places: [(String, CLLocationCoordinate2D)] = [
            ("Boston", at(42.3601, -71.0589)),
            ("Stowe VT", at(44.4654, -72.6874)),
            ("Fort Kent ME", at(47.2587, -68.5895)),
            ("Lubec ME", at(44.8606, -66.9842)),
            ("Bar Harbor ME", at(44.3876, -68.2039)),
            ("Greenwich CT", at(41.0262, -73.6282)),
            ("Nantucket", at(41.2835, -70.0995)),
            ("Block Island RI", at(41.1720, -71.5578)),
            ("Grand Isle VT", at(44.7184, -73.2968)),
            ("Pittsburg NH", at(45.0512, -71.3920)),
            ("Provincetown", at(42.0584, -70.1786)),
        ]
        for (name, point) in places {
            XCTAssertTrue(NewEngland.contains(point), "\(name) is in New England")
        }
    }

    func test_the_islands_with_roads_are_kept() {
        // Simplification is where small islands die. The script keeps every
        // one; these are the ones the brief named.
        let islands: [(String, CLLocationCoordinate2D)] = [
            ("Martha's Vineyard, Edgartown", at(41.3890, -70.5134)),
            ("Aquidneck, Newport", at(41.4901, -71.3128)),
            ("Conanicut, Jamestown", at(41.4968, -71.3673)),
            ("Mount Desert, Northeast Harbor", at(44.2959, -68.2856)),
            ("Deer Isle", at(44.2237, -68.6778)),
            ("Vinalhaven", at(44.0484, -68.8350)),
            ("Peaks Island", at(43.6556, -70.1990)),
            ("North Hero, Lake Champlain", at(44.8303, -73.2729)),
            ("Isle La Motte, Lake Champlain", at(44.8862, -73.3420)),
        ]
        for (name, point) in islands {
            XCTAssertTrue(NewEngland.contains(point), "\(name) is in New England")
        }
    }

    func test_points_within_a_kilometre_of_a_border_are_inside() {
        // Near-border points, labelled with their measured distance to the
        // edge of the Census outline. They pass because the outline was
        // pushed 500 m out before it was simplified.
        let nearBorder: [(String, CLLocationCoordinate2D)] = [
            ("Derby Line VT, 70 m from Quebec", at(45.0050, -72.0990)),
            ("Byram, Greenwich CT, 120 m from New York", at(41.0060, -73.6560)),
            ("Lubec ME, 150 m from the Lubec Narrows, facing Campobello NB", at(44.8606, -66.9842)),
            ("Fort Kent ME, 300 m from the St. John River and New Brunswick", at(47.2587, -68.5895)),
            ("Madawaska ME, 500 m from the St. John River", at(47.3556, -68.3317)),
            ("Calais ME, 830 m from the St. Croix River and New Brunswick", at(45.1840, -67.2770)),
        ]
        for (name, point) in nearBorder {
            XCTAssertTrue(NewEngland.contains(point), name)
        }
    }

    func test_a_fix_just_outside_the_census_line_still_counts() {
        // All three fall *outside* the raw Census outline, which is clipped to
        // a generalised shore and border. This is what the buffer is for.
        XCTAssertTrue(NewEngland.contains(at(44.2959, -68.2856)),
                      "Northeast Harbor's dock, 10 m off the Census shore")
        XCTAssertTrue(NewEngland.contains(at(45.0060, -72.1420)),
                      "Beebe Plain VT, on the Quebec line")
        XCTAssertTrue(NewEngland.contains(at(47.4597, -69.2240)),
                      "Estcourt Station ME, the northern tip, 20 m out")
    }

    func test_water_enclosed_by_new_england_is_new_england() {
        // Buffering closes island chains around the water behind them, which
        // left holes in the outline. Holed, someone on a ferry in Casco Bay
        // would be told they were not in New England. The holes are filled.
        XCTAssertTrue(NewEngland.contains(at(43.7112, -70.1855)), "Casco Bay")
        XCTAssertTrue(NewEngland.contains(at(42.2790, -70.9186)), "Boston Harbor")
    }

    // MARK: - Outside

    func test_the_named_places_are_outside() {
        // Each at least 3 km from New England, measured: the nearest is
        // Hoosick Falls at 6.2 km. Edmundston's centre is only 1.5 km from
        // Madawaska, so its Saint-Jacques district stands in for it.
        let places: [(String, CLLocationCoordinate2D)] = [
            ("Cupertino, 4,090 km", at(37.3349, -122.0090)),
            ("Albany NY, 35.9 km", at(42.6526, -73.7562)),
            ("Montauk NY, 30.6 km", at(41.0359, -71.9545)),
            ("Sherbrooke QC, 39.8 km", at(45.4042, -71.8929)),
            ("Plattsburgh NY, 6.8 km", at(44.6995, -73.4529)),
            ("Edmundston NB, Saint-Jacques, 9.7 km", at(47.4426, -68.3829)),
            ("Hoosick Falls NY, 6.2 km", at(42.9012, -73.3515)),
        ]
        for (name, point) in places {
            XCTAssertFalse(NewEngland.contains(point), "\(name) is not in New England")
        }
    }

    func test_the_buffer_stops_well_short_of_a_kilometre_over_the_line() {
        // The outline reaches at most 697 m from Census land (measured by the
        // script, and printed in the generated file's header).
        XCTAssertFalse(NewEngland.contains(at(47.3737, -68.3251)),
                       "Edmundston's centre, 1.5 km over the St. John")
        XCTAssertFalse(NewEngland.contains(at(44.9940, -73.3650)),
                       "Rouses Point NY, 1.0 km from Vermont")
        XCTAssertFalse(NewEngland.contains(at(43.5550, -73.4030)),
                       "Whitehall NY, 1.5 km from Vermont")
    }

    func test_a_meaningless_coordinate_is_outside() {
        XCTAssertFalse(NewEngland.contains(at(0, 0)), "CoreLocation's junk fix")
        XCTAssertFalse(NewEngland.contains(kCLLocationCoordinate2DInvalid))
        XCTAssertFalse(NewEngland.contains(at(.nan, .nan)))
    }

    func test_a_rectangle_cannot_stand_in_for_the_outline() {
        // Trap 2 in the brief, as a test: the envelope is a fine search
        // region and a wrong answer to "is this in New England?".
        let envelope = MKCoordinateRegion.newEnglandEnvelope
        func inEnvelope(_ point: CLLocationCoordinate2D) -> Bool {
            abs(point.latitude - envelope.center.latitude) <= envelope.span.latitudeDelta / 2
                && abs(point.longitude - envelope.center.longitude) <= envelope.span.longitudeDelta / 2
        }
        for point in [at(41.0359, -71.9545), at(45.4042, -71.8929), at(47.4426, -68.3829)] {
            XCTAssertTrue(inEnvelope(point), "Montauk, Sherbrooke and Edmundston are in the box")
            XCTAssertFalse(NewEngland.contains(point), "and not in New England")
        }
    }

    func test_the_envelope_holds_the_whole_outline() {
        let envelope = MKCoordinateRegion.newEnglandEnvelope
        XCTAssertLessThan(envelope.center.latitude - envelope.span.latitudeDelta / 2,
                          NewEnglandBoundary.south)
        XCTAssertGreaterThan(envelope.center.latitude + envelope.span.latitudeDelta / 2,
                             NewEnglandBoundary.north)
        XCTAssertLessThan(envelope.center.longitude - envelope.span.longitudeDelta / 2,
                          NewEnglandBoundary.west)
        XCTAssertGreaterThan(envelope.center.longitude + envelope.span.longitudeDelta / 2,
                             NewEnglandBoundary.east)
        // Fort Kent and Lubec are what the camera box leaves out.
        XCTAssertGreaterThan(NewEnglandBoundary.north, 47.2587)
        XCTAssertGreaterThan(NewEnglandBoundary.east, -66.9842)
    }

    // MARK: - Suggestions, from captured strings

    func test_new_england_suggestions_are_kept() {
        let kept: [(String, String)] = [
            ("Portland, ME", "United States"),
            ("Portland, CT", "United States"),
            ("Portland St", "Boston, MA, United States"),
            ("155 on Portland", "155 Portland St, Boston, MA  02114, United States"),
            ("Portland International Jetport", "1001 Westbrook Street, Portland, ME 04102, United States"),
            ("Portland Head Light", "1000 Shore Rd, Cape Elizabeth, ME  04107, United States"),
            ("Main St", "Charlestown, MA, United States"),
            ("Concord, NH", "United States"),
            ("Stowe, VT", "United States"),
            ("Stowe Mountain Resort", "5781 Mountain Rd, Stowe, VT  05672, United States"),
            ("Albany Twp, ME", "United States"),
            ("Manchester-by-the-Sea, MA", "United States"),
            ("Sherbrooke Ave", "Lewiston, ME, United States"),
            ("Sherbrooke Rd", "Newton, MA, United States"),
            ("Paris", "South Paris, ME, United States"),
            ("Fort Kent Village", "Fort Kent, ME, United States"),
            ("Mt. Washington State Park",
             "1598 Mt Washington Auto Road, Sargent's Purchase, NH 03589, United States"),
            ("Dunkin'", "100 Cambridge St, Boston, MA  02114, United States"),
            ("Greenwich Ave", "Warwick, RI, United States"),
        ]
        for (title, subtitle) in kept {
            XCTAssertTrue(NewEngland.allowsSuggestion(title: title, subtitle: subtitle),
                          "\(title) / \(subtitle)")
        }
    }

    func test_a_suggestion_that_names_no_place_at_all_is_kept() {
        // Two real Boston-area results arrive with nothing after the street.
        // Dropping them would hide good places; `firstInside` checks them.
        XCTAssertTrue(NewEngland.allowsSuggestion(title: "Starbucks Coffee Company",
                                                  subtitle: "65-66 Beacon St"))
        XCTAssertTrue(NewEngland.allowsSuggestion(title: "Omni Mount Washington Resort & Spa",
                                                  subtitle: "310 Mount Washington Hotel Road"))
        XCTAssertTrue(NewEngland.allowsSuggestion(title: "Somewhere", subtitle: ""))
    }

    func test_a_city_in_another_state_is_dropped_by_its_title() {
        // The case a subtitle-only filter misses: the state is in the title,
        // and the subtitle says only "United States".
        let dropped: [(String, String)] = [
            ("Portland, OR", "United States"),
            ("Portland, MI", "United States"),
            ("Concord, CA", "United States"),
            ("Albany, NY", "United States"),
            ("Montauk, NY", "United States"),
            ("Plattsburgh, NY", "United States"),
            ("Springfield, MO", "United States"),
            ("Burlington, ON", "Canada"),
            ("Sherbrooke, QC", "Canada"),
            ("Edmundston, NB", "Canada"),
            ("Fort Kent, AB", "Canada"),
        ]
        for (title, subtitle) in dropped {
            XCTAssertFalse(NewEngland.allowsSuggestion(title: title, subtitle: subtitle),
                           "\(title) / \(subtitle)")
        }
    }

    func test_a_place_in_another_state_is_dropped_by_its_subtitle() {
        let dropped: [(String, String)] = [
            ("Times Square", "1560 Broadway, Unit 1001, New York, NY  10036, United States"),
            ("Times Square", "Manhattan, New York, NY, United States"),
            ("Times Square–42 Street Station", "New York, NY, United States"),
            ("Greenwich Village", "Manhattan, New York, NY, United States"),
            ("Mount Washington", "Los Angeles, CA, United States"),
            ("Albany International Airport", "737 NY-155 W, Loudonville, NY  12211, United States"),
            ("Portland International Airport", "7000 NE Airport Way, Portland, OR 97218-1009, United States"),
            ("Sherbrooke", "Montréal QC, Canada"),
            ("Université de Sherbrooke", "2500 Boul de l'Université, Sherbrooke QC J1K 2R1, Canada"),
            ("Sherbrooke", "St. Mary's, NS, Canada"),
            ("Edmundston Airport", "30 ch. de l'Aéroport, Saint-Jacques DSL NB E7B 2Z6, Canada"),
            ("Lubec Narrows", "Campobello Island, NB, Canada"),
        ]
        for (title, subtitle) in dropped {
            XCTAssertFalse(NewEngland.allowsSuggestion(title: title, subtitle: subtitle),
                           "\(title) / \(subtitle)")
        }
    }

    func test_a_place_abroad_is_dropped_by_its_country() {
        // No state code anywhere, so the subtitle's last part decides.
        // England is not a country name ISO knows; Apple writes it anyway.
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
            XCTAssertFalse(NewEngland.allowsSuggestion(title: title, subtitle: subtitle),
                           "\(title) / \(subtitle)")
        }
    }

    func test_codes_are_matched_as_words_not_letters() {
        // "ME" inside a word is not Maine, and "NE" in front of a street name
        // is a direction, not Nebraska. A substring match would drop both.
        XCTAssertTrue(NewEngland.allowsSuggestion(title: "Café", subtitle: "100 NE Main St"))
        XCTAssertTrue(NewEngland.allowsSuggestion(title: "Wayne St", subtitle: "12 WAYNE ST"))
        XCTAssertTrue(NewEngland.allowsSuggestion(title: "Homestead", subtitle: "HOMESTEAD RD, Camden, ME"))
        XCTAssertFalse(NewEngland.allowsSuggestion(title: "Home Depot", subtitle: "HOMESTEAD, FL 33030"))
    }

    func test_the_last_code_in_an_address_is_the_one_that_counts() {
        // A New York route number before a New England state: the state wins,
        // in either direction.
        XCTAssertTrue(NewEngland.allowsSuggestion(title: "Gas", subtitle: "NY 22, Amenia Rd, Sharon, CT 06069"))
        XCTAssertFalse(NewEngland.allowsSuggestion(title: "Gas", subtitle: "VT 9, Hoosick, NY 12089"))
    }

    // MARK: - The resolve gate

    func test_a_result_in_new_england_is_accepted() {
        // Coordinates and states as MKLocalSearch returned them.
        XCTAssertTrue(NewEngland.accepts(at(43.6590, -70.2569), administrativeArea: "ME"), "Portland")
        XCTAssertTrue(NewEngland.accepts(at(44.4654, -72.6860), administrativeArea: "VT"), "Stowe")
        XCTAssertTrue(NewEngland.accepts(at(41.0323, -73.6256), administrativeArea: "CT"), "Greenwich")
        XCTAssertTrue(NewEngland.accepts(at(42.3625, -71.0876), administrativeArea: nil), "no state named")
        XCTAssertTrue(NewEngland.accepts(at(42.3625, -71.0876), administrativeArea: ""))
        XCTAssertTrue(NewEngland.accepts(at(42.3625, -71.0876), administrativeArea: "Massachusetts"))
        XCTAssertTrue(NewEngland.accepts(at(42.3625, -71.0876), administrativeArea: "ma"))
    }

    func test_a_result_elsewhere_is_refused() {
        XCTAssertFalse(NewEngland.accepts(at(45.5151, -122.6795), administrativeArea: "OR"), "Portland OR")
        XCTAssertFalse(NewEngland.accepts(at(40.7555, -73.9866), administrativeArea: "NY"), "Times Square")
        XCTAssertFalse(NewEngland.accepts(at(45.4042, -71.8929), administrativeArea: "QC"), "Sherbrooke")
        XCTAssertFalse(NewEngland.accepts(at(42.6512, -73.7518), administrativeArea: "NY"), "Albany")
        XCTAssertFalse(NewEngland.accepts(at(48.8568, 2.3511), administrativeArea: "Île-de-France"), "Paris")
    }

    func test_a_place_over_the_line_is_refused_by_its_state() {
        // Stanstead, Quebec, is 370 m from Vermont: inside the buffered
        // outline. Its state is what keeps it out.
        let stanstead = at(45.0090, -72.0970)
        XCTAssertTrue(NewEngland.contains(stanstead), "precondition: the buffer reaches it")
        XCTAssertFalse(NewEngland.accepts(stanstead, administrativeArea: "QC"))
    }

    private func item(_ point: CLLocationCoordinate2D, state: String) -> MKMapItem {
        let address = CNMutablePostalAddress()
        address.state = state
        return MKMapItem(placemark: MKPlacemark(coordinate: point, postalAddress: address))
    }

    func test_the_first_result_in_new_england_wins_not_the_first_result() {
        // From Cupertino on `main`, a typed "Portland" resolved to Oregon,
        // because Apple ranked it first.
        let oregon = item(at(45.5151, -122.6795), state: "OR")
        let maine = item(at(43.6590, -70.2569), state: "ME")
        XCTAssertEqual(oregon.placemark.administrativeArea, "OR", "precondition: the fixture carries a state")

        let chosen = NewEngland.firstInside([oregon, maine])
        XCTAssertEqual(chosen?.placemark.administrativeArea, "ME")
        XCTAssertNil(NewEngland.firstInside([oregon]), "never an out-of-region item")
        XCTAssertNil(NewEngland.firstInside([]))
    }

    func test_the_refusal_names_the_place_and_the_region() {
        XCTAssertEqual(NewEngland.notInNewEngland("Times Square"),
                       "“Times Square” isn’t in New England. Sunday Drive only covers the six New England states.")
    }

    // MARK: - The search bias

    func test_a_bias_inside_new_england_is_left_alone() {
        // Ranking near the user is what keeps "main street" local.
        let boston = MKCoordinateRegion.around(at(42.3601, -71.0589))
        let bias = NewEngland.searchBias(around: boston)
        XCTAssertFalse(bias.restricted, "required on 30 km, Stowe from Boston would find nothing")
        XCTAssertEqual(bias.region.center.latitude, boston.center.latitude, accuracy: 1e-9)
        XCTAssertEqual(bias.region.span.latitudeDelta, boston.span.latitudeDelta, accuracy: 1e-9)
    }

    func test_a_bias_that_has_left_new_england_becomes_the_envelope() {
        let envelope = MKCoordinateRegion.newEnglandEnvelope
        for region in [MKCoordinateRegion.around(at(37.3349, -122.0090)),   // Cupertino
                       MKCoordinateRegion.around(at(43.0, -69.0)),          // the Gulf of Maine
                       MKCoordinateRegion.around(at(45.4042, -71.8929))] {  // Sherbrooke
            let bias = NewEngland.searchBias(around: region)
            XCTAssertTrue(bias.restricted)
            XCTAssertEqual(bias.region.center.latitude, envelope.center.latitude, accuracy: 1e-9)
            XCTAssertEqual(bias.region.span.longitudeDelta, envelope.span.longitudeDelta, accuracy: 1e-9)
        }
    }

    func test_a_bias_wider_than_new_england_becomes_the_envelope() {
        // The opening camera as MapKit reported it on an iPhone SE, widened to
        // the card's shape. Its centre is in western Maine, so only the width
        // decides this.
        let wide = MKCoordinateRegion(center: at(45.05, -70.34),
                                      span: MKCoordinateSpan(latitudeDelta: 9.3, longitudeDelta: 16.13))
        XCTAssertTrue(NewEngland.contains(wide.center), "precondition: the centre is inside")
        XCTAssertTrue(NewEngland.searchBias(around: wide).restricted)
    }
}
