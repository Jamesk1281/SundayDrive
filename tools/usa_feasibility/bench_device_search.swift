// The scenic (pref 1) search as a phone would run it, on a whole region.
//
//     python tools/usa_feasibility/export_search_graph.py pipeline <processed> <out.bin> 40
//     swiftc -O tools/usa_feasibility/bench_device_search.swift -o <dir>/bench
//     <dir>/bench <out.bin>
//
// Recomputes every directed weight from the scenery vector (Router._weights at
// pref 1, default beauty weights), then runs a binary-heap Dijkstra three ways:
// the whole graph, stopping at the destination, and stopping at the destination
// while ignoring nodes outside the corridor |sv| + |vt| <= 1.5 d + 20 km. Every
// answer is checked against scipy's whole-graph optimum from the export.
// Runs on the Mac; a recent iPhone's performance core is in the same class.

import Foundation

let data = try! Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]), options: .alwaysMapped)
var off = 0
func take<T>(_ count: Int, _ type: T.Type) -> [T] {
    let bytes = count * MemoryLayout<T>.stride
    let out = [T](unsafeUninitializedCapacity: count) { buf, n in
        data.withUnsafeBytes { raw in
            _ = memcpy(buf.baseAddress!, raw.baseAddress!.advanced(by: off), bytes)
        }
        n = count
    }
    off += bytes
    return out
}
let head = take(5, Int64.self)
let n = Int(head[0]), nPairs = Int(head[1]), nSlots = Int(head[2]), nEdges = Int(head[3]), nTests = Int(head[4])
let indptr = take(n + 1, Int64.self).map { Int($0) }
let heads = take(nPairs, Int32.self)
let slotPair = take(nSlots, Int32.self), eidx = take(nSlots, Int32.self)
let dmin = take(nSlots, Float.self), extra = take(nSlots, Float.self)
let km = take(nEdges, Float.self), unp = take(nEdges, Float.self)
let base = take(nEdges, Float.self), adj = take(nEdges, Float.self)
let pm = take(nEdges * 6, Float.self)
let xs = take(n, Float.self), ys = take(n, Float.self)
let tS = take(nTests, Int32.self), tT = take(nTests, Int32.self)
let tD = take(nTests, Float.self), tC = take(nTests, Double.self)

func now() -> Double { Double(DispatchTime.now().uptimeNanoseconds) / 1e9 }

// --- per-request weights (what a phone does when the sliders change) --------
var pairW = [Float](repeating: .infinity, count: nPairs)
func reweight(_ beauty: [Float]) {
    for p in 0..<nPairs { pairW[p] = .infinity }
    pairW.withUnsafeMutableBufferPointer { pw in
        for i in 0..<nSlots {
            let e = Int(eidx[i]), b = e * 6
            var raw = base[e]
            for k in 0..<6 { raw += pm[b + k] * beauty[k] }
            let score = 10 * min(max((raw + 0.143) * 1.2 + adj[e], 0), 1)
            let w = dmin[i] + 8 * km[e] * (1 - score / 10) + km[e] * unp[e] + extra[i]
            let p = Int(slotPair[i])
            if w < pw[p] { pw[p] = w }
        }
    }
}
var tw: [Double] = []
for _ in 0..<5 { let t0 = now(); reweight([1, 1, 1, 1, 1, 1]); tw.append(now() - t0) }

// --- binary-heap Dijkstra ----------------------------------------------------
struct Heap {
    var k: [Float] = [], v: [Int32] = []
    var isEmpty: Bool { k.isEmpty }
    mutating func push(_ key: Float, _ val: Int32) {
        k.append(key); v.append(val)
        var i = k.count - 1
        while i > 0 { let p = (i - 1) >> 1; if k[p] <= k[i] { break }; k.swapAt(p, i); v.swapAt(p, i); i = p }
    }
    mutating func pop() -> (Float, Int32) {
        let top = (k[0], v[0]); let lk = k.removeLast(), lv = v.removeLast()
        if !k.isEmpty {
            k[0] = lk; v[0] = lv
            var i = 0
            while true {
                let l = 2 * i + 1, r = l + 1; var m = i
                if l < k.count && k[l] < k[m] { m = l }
                if r < k.count && k[r] < k[m] { m = r }
                if m == i { break }
                k.swapAt(i, m); v.swapAt(i, m); i = m
            }
        }
        return top
    }
}
var dist = [Float](repeating: .infinity, count: n)
var touched: [Int32] = []
func search(_ s: Int, _ t: Int, stopAtTarget: Bool, corridor: Float?) -> (Float, Int) {
    for v in touched { dist[Int(v)] = .infinity }
    touched.removeAll(keepingCapacity: true)
    var heap = Heap(); var settled = 0
    dist[s] = 0; touched.append(Int32(s)); heap.push(0, Int32(s))
    let sx = xs[s], sy = ys[s], ex = xs[t], ey = ys[t]
    while !heap.isEmpty {
        let (c, u32) = heap.pop(); let u = Int(u32)
        if c > dist[u] { continue }
        settled += 1
        if stopAtTarget && u == t { return (c, settled) }
        for a in indptr[u]..<indptr[u + 1] {
            let v = Int(heads[a]); let nc = c + pairW[a]
            if nc < dist[v] {
                if let lim = corridor {
                    let dx1 = xs[v] - sx, dy1 = ys[v] - sy, dx2 = xs[v] - ex, dy2 = ys[v] - ey
                    if (dx1 * dx1 + dy1 * dy1).squareRoot() + (dx2 * dx2 + dy2 * dy2).squareRoot() > lim { continue }
                }
                if dist[v] == .infinity { touched.append(Int32(v)) }
                dist[v] = nc; heap.push(nc, Int32(v))
            }
        }
    }
    return (dist[t], settled)
}

func median(_ a: [Double]) -> Double { let s = a.sorted(); return s[s.count / 2] }
func p90(_ a: [Double]) -> Double { let s = a.sorted(); return s[min(s.count - 1, Int(Double(s.count) * 0.9))] }
print("graph: \(n) nodes, \(nPairs) directed pairs; reweight all \(nSlots) slots: median \(String(format: "%.1f", 1e3 * median(tw))) ms")
for (label, stop, useCorridor) in [("whole graph", false, false), ("stop at destination", true, false),
                                    ("stop at destination, corridor only", true, true)] {
    var times: [Double] = [], settledShare: [Double] = [], worst = 0.0
    for i in 0..<nTests {
        let s = Int(tS[i]), t = Int(tT[i]), d = tD[i]
        let t0 = now()
        let (c, settled) = search(s, t, stopAtTarget: stop, corridor: useCorridor ? 1.5 * d + 20 : nil)
        times.append(now() - t0); settledShare.append(Double(settled) / Double(n))
        worst = max(worst, abs(Double(c) / tC[i] - 1))
    }
    print(String(format: "%-36@ median %6.1f ms  p90 %6.1f ms  settled median %5.1f%%  worst cost error %.2e",
                 label as NSString, 1e3 * median(times), 1e3 * p90(times), 100 * median(settledShare), worst))
}
