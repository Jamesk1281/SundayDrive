// How long an on-device rejoin takes, on a real corridor graph.
//
//     .venv/bin/python tools/corridor_study.py --export --out <dir>
//     swiftc -O tools/bench_corridor_dijkstra.swift -o <dir>/bench
//     <dir>/bench <dir>/bench-*.bin    (bench-route.bin, bench-loop400.bin)
//
// Written for `docs/mid-drive-recovery-plan.md`, tier T1. `corridor_study.py
// --export` writes the search graph of a 500 m corridor (the router's own
// turn-restriction-split nodes and its blended weights at the route's pref),
// the route's nodes inside it with each one's cost still to drive, and 32
// evenly spaced start nodes. This runs the search the phone would: a plain
// binary-heap Dijkstra from the start, then the cheapest "reach a route node,
// then follow the route" total. Nothing clever — no A*, no early exit — so the
// number is an upper bound on a first implementation, not a best case.
//
// It runs on the Mac. An iPhone's performance cores are within a small factor
// of an M2's for a single-threaded, cache-bound loop like this, and the plan
// says so rather than claiming a phone measurement it did not take.

import Foundation

struct Corridor {
    let n: Int
    let indptr: [Int64]
    let indices: [Int32]
    let weights: [Float]
    let ahead: [Int32]
    let togo: [Float]
    let sources: [Int32]
}

func load(_ path: String) -> Corridor {
    let data = try! Data(contentsOf: URL(fileURLWithPath: path))
    var offset = 0
    func take<T>(_ count: Int, _ type: T.Type) -> [T] {
        let size = MemoryLayout<T>.stride * count
        let out = data[offset..<offset + size].withUnsafeBytes { raw in
            Array(raw.bindMemory(to: T.self))
        }
        offset += size
        return out
    }
    let header = take(4, Int64.self)
    let n = Int(header[0]), nnz = Int(header[1]), nAhead = Int(header[2]), nSrc = Int(header[3])
    return Corridor(n: n, indptr: take(n + 1, Int64.self), indices: take(nnz, Int32.self),
                    weights: take(nnz, Float.self), ahead: take(nAhead, Int32.self),
                    togo: take(nAhead, Float.self), sources: take(nSrc, Int32.self))
}

/// A binary min-heap of (cost, node), lazy deletion.
struct Heap {
    var keys: [Float] = []
    var vals: [Int32] = []
    var isEmpty: Bool { keys.isEmpty }
    mutating func push(_ k: Float, _ v: Int32) {
        keys.append(k); vals.append(v)
        var i = keys.count - 1
        while i > 0 {
            let p = (i - 1) / 2
            if keys[p] <= keys[i] { break }
            keys.swapAt(p, i); vals.swapAt(p, i); i = p
        }
    }
    mutating func pop() -> (Float, Int32) {
        let top = (keys[0], vals[0])
        let lastK = keys.removeLast(), lastV = vals.removeLast()
        if !keys.isEmpty {
            keys[0] = lastK; vals[0] = lastV
            var i = 0
            while true {
                let l = 2 * i + 1, r = l + 1
                var m = i
                if l < keys.count, keys[l] < keys[m] { m = l }
                if r < keys.count, keys[r] < keys[m] { m = r }
                if m == i { break }
                keys.swapAt(m, i); vals.swapAt(m, i); i = m
            }
        }
        return top
    }
}

func rejoin(_ c: Corridor, from source: Int32, dist: inout [Float]) -> (Float, Int) {
    for i in 0..<dist.count { dist[i] = .infinity }
    var heap = Heap()
    heap.keys.reserveCapacity(1024); heap.vals.reserveCapacity(1024)
    dist[Int(source)] = 0
    heap.push(0, source)
    var settled = 0
    while !heap.isEmpty {
        let (d, u) = heap.pop()
        if d > dist[Int(u)] { continue }
        settled += 1
        let lo = Int(c.indptr[Int(u)]), hi = Int(c.indptr[Int(u) + 1])
        var k = lo
        while k < hi {
            let v = Int(c.indices[k])
            let nd = d + c.weights[k]
            if nd < dist[v] { dist[v] = nd; heap.push(nd, Int32(v)) }
            k += 1
        }
    }
    var best = Float.infinity
    for (i, node) in c.ahead.enumerated() {
        best = min(best, dist[Int(node)] + c.togo[i])
    }
    return (best, settled)
}

for path in CommandLine.arguments.dropFirst() {
    let c = load(path)
    var dist = [Float](repeating: .infinity, count: c.n)
    var times: [Double] = []
    var reached = 0
    var settledTotal = 0
    // One warm-up pass, then every source three times.
    _ = rejoin(c, from: c.sources[0], dist: &dist)
    for _ in 0..<3 {
        for s in c.sources {
            let t0 = DispatchTime.now().uptimeNanoseconds
            let (best, settled) = rejoin(c, from: s, dist: &dist)
            times.append(Double(DispatchTime.now().uptimeNanoseconds - t0) / 1e6)
            if best.isFinite { reached += 1 }
            settledTotal += settled
        }
    }
    times.sort()
    let p = { (q: Double) in times[min(times.count - 1, Int(q * Double(times.count)))] }
    print(String(format: "%@: %d nodes, %d arcs, %d route nodes; per search p50 %.2f ms, p90 %.2f ms, max %.2f ms; %d/%d reached the route; mean settled %d",
                 (path as NSString).lastPathComponent, c.n, c.indices.count, c.ahead.count,
                 p(0.5), p(0.9), times.last!, reached, times.count, settledTotal / times.count))
}
