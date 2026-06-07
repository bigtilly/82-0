(globalThis.TURBOPACK || (globalThis.TURBOPACK = [])).push(["object" == typeof document ? document.currentScript : void 0, 23750, 10708, 68793, 93290, e => {
    "use strict";
    var t = e.i(68866)
      , a = e.i(47163);
    function r({className: e, type: r, ...n}) {
        return (0,
        t.jsx)("input", {
            type: r,
            "data-slot": "input",
            className: (0,
            a.cn)("file:text-foreground placeholder:text-muted-foreground selection:bg-primary selection:text-primary-foreground dark:bg-input/30 border-input h-9 w-full min-w-0 rounded-md border bg-transparent px-3 py-1 text-base shadow-xs transition-[color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm", "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]", "aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive", e),
            ...n
        })
    }
    e.s(["Input", () => r], 23750);
    var n = e.i(87890)
      , i = e.i(9424)
      , l = n.forwardRef( (e, a) => (0,
    t.jsx)(i.Primitive.label, {
        ...e,
        ref: a,
        onMouseDown: t => {
            t.target.closest("button, input, select, textarea") || (e.onMouseDown?.(t),
            !t.defaultPrevented && t.detail > 1 && t.preventDefault())
        }
    }));
    function s({className: e, ...r}) {
        return (0,
        t.jsx)(l, {
            "data-slot": "label",
            className: (0,
            a.cn)("flex items-center gap-2 text-sm leading-none font-medium select-none group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:opacity-50", e),
            ...r
        })
    }
    l.displayName = "Label",
    e.s(["Label", () => s], 10708);
    var o = e.i(10965);
    let d = (0,
    o.default)("Eye", [["path", {
        d: "M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0",
        key: "1nclc0"
    }], ["circle", {
        cx: "12",
        cy: "12",
        r: "3",
        key: "1v7zrd"
    }]]);
    e.s(["Eye", () => d], 68793);
    let p = (0,
    o.default)("EyeOff", [["path", {
        d: "M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49",
        key: "ct8e1f"
    }], ["path", {
        d: "M14.084 14.158a3 3 0 0 1-4.242-4.242",
        key: "151rxh"
    }], ["path", {
        d: "M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143",
        key: "13bj9a"
    }], ["path", {
        d: "m2 2 20 20",
        key: "1ooewy"
    }]]);
    e.s(["EyeOff", () => p], 93290)
}
, 23902, 17428, e => {
    "use strict";
    let t = !1
      , a = null
      , r = null
      , n = []
      , i = ["https://firebasestorage.googleapis.com/v0/b/project-4599904239656435772.firebasestorage.app/o/players_flat.json?alt=media"]
      , l = "nba_players_local_cache";
    async function s() {
        return Promise.all(i.map(async e => {
            let t = await fetch(e);
            if (!t.ok)
                throw Error(`Failed to fetch ${e}: ${t.status}`);
            return t.json()
        }
        ))
    }
    function o(e) {
        a = 1 === e.length ? e[0] : e.every(e => Array.isArray(e)) ? e.flat() : e.reduce( (e, t) => ({
            ...e,
            ...t
        }), {}),
        t = !0,
        n = r = c();
        try {
            localStorage.setItem(l, JSON.stringify({
                version: "v2",
                timestamp: Date.now(),
                data: a
            }))
        } catch (e) {}
        return r
    }
    async function d() {
        if (t && null !== r)
            return r;
        let e = function() {
            try {
                let e = localStorage.getItem(l);
                if (!e)
                    return null;
                let t = JSON.parse(e)
                  , a = Date.now();
                if ("v2" === t.version && a - t.timestamp < 6048e5 && t.data)
                    return t.data
            } catch (e) {}
            return null
        }();
        return e ? o([e]) : o(await s())
    }
    async function p() {
        if (!t || null === r)
            try {
                await d()
            } catch (e) {
                t = !1,
                n = []
            }
    }
    function c() {
        let e;
        if (!a || 0 === Object.keys(a).length)
            return [];
        if (Array.isArray(a)) {
            let t = {};
            a.forEach(e => {
                let a = e.team
                  , r = e.era;
                a && r && (t[a] || (t[a] = {}),
                t[a][r] || (t[a][r] = []),
                t[a][r].push(e))
            }
            ),
            e = t
        } else
            e = a;
        return Object.entries(e).map( ([e,t], a) => {
            let r = {};
            return ["1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s"].forEach(n => {
                t[n] && (r[n] = t[n].map(t => ({
                    ...t,
                    team: e,
                    decade: n,
                    teamId: a,
                    positions: Array.isArray(t.positions) ? t.positions.filter(e => "nan" !== e && null != e) : [t.pos].filter(e => "nan" !== e && null != e)
                })).filter(e => {
                    let t = e.ppg ?? 0
                      , a = e.rpg ?? 0
                      , r = e.apg ?? 0
                      , n = e.spg ?? 0
                      , i = e.bpg ?? 0;
                    return !isNaN(t) && !isNaN(a) && !isNaN(r) && !isNaN(n) && !isNaN(i)
                }
                ))
            }
            ),
            {
                id: a,
                abbreviation: e,
                name: e,
                decades: r
            }
        }
        ).filter(e => Object.keys(e.decades).length > 0)
    }
    function g() {
        return null !== r ? r : r = c()
    }
    function u(e, t) {
        let a = g().find(t => t.id === e)
          , r = C[t] || t;
        return a && a.decades[r] ? a.decades[r] : []
    }
    function F(e) {
        let t = g().find(t => t.id === e);
        return t ? t.abbreviation : "Unknown Team"
    }
    function f(e, t, a) {
        let r = g().find(e => e.abbreviation === t);
        return r && r.decades[a] && r.decades[a].find(t => t.player === e) || null
    }
    function m(e, t) {
        return e.positions.includes(t)
    }
    function b(e, t, a) {
        if (t === a)
            return !1;
        let r = e[t]
          , n = e[a];
        return (!r || !!m(r, a)) && (!n || !!m(n, t))
    }
    function h(e) {
        return e.positions
    }
    let C = {
        "60's": "1960s",
        "70's": "1970s",
        "80's": "1980s",
        "90's": "1990s",
        "00's": "2000s",
        "10's": "2010s",
        "20's": "2020s"
    }
      , y = {
        "Wilt Chamberlain": "Wilt",
        "Giannis Antetokounmpo": "Giannis",
        "Shai Gilgeous-Alexander": "SGA",
        "Kareem Abdul-Jabbar": "Kareem"
    };
    function E(e) {
        return y[e] || e
    }
    e.s(["DECADES", 0, ["60's", "70's", "80's", "90's", "00's", "10's", "20's"], "POSITIONS", 0, ["PG", "SG", "SF", "PF", "C"], "TEAMS", () => n, "canPlayerPlayPosition", () => m, "canSwapPositions", () => b, "fetchPlayerDatasets", () => s, "findPlayer", () => f, "getDisplayName", () => E, "getPlayerPositions", () => h, "getPlayersByTeamAndDecade", () => u, "getTeamName", () => F, "getTeams", () => g, "hydratePlayerData", () => o, "initializeFirestoreData", () => p], 23902);
    let A = {
        ATL: ["#E03A3E", "#FFFFFF"],
        BOS: ["#007A33", "#FFFFFF", "#00A846"],
        BKN: ["#000000", "#FFFFFF", "#777777"],
        CHA: ["#00788C", "#FFFFFF", "#00788C", "#00ADCB"],
        CHI: ["#CE1141", "#FFFFFF"],
        CLE: ["#6F263D", "#FFB81C", "#6F263D", "#FFB81C"],
        DAL: ["#002B5E", "#C4CED4", "#0053BC"],
        DEN: ["#0E2240", "#FEC524", "#0E2240", "#FEC524"],
        DET: ["#C8102E", "#FFFFFF", "#C8102E", "#F11438"],
        GSW: ["#1D428A", "#FDB927", "#1D428A", "#FDB927"],
        HOU: ["#CE1141", "#FFFFFF"],
        IND: ["#041E42", "#FFC72C", "#041E42", "#FFC72C"],
        LAC: ["#1D428A", "#FFFFFF", "#4169C8"],
        LAL: ["#552583", "#FDB927", "#552583", "#FDB927"],
        MEM: ["#5D76A9", "#FFFFFF", "#5D76A9", "#88B0FF"],
        MIA: ["#000000", "#F9423A"],
        MIL: ["#00471B", "#EEE1C6", "#00813A", "#EEE1C6"],
        MIN: ["#0C2340", "#78BE20", "#78BE20"],
        NOP: ["#0C2340", "#B4975A", "#0C2340", "#B4975A"],
        NYK: ["#006BB6", "#F58426", "#006BB6", "#F58426"],
        OKC: ["#002D62", "#EF3B24", "#EF3B24"],
        ORL: ["#0077C0", "#C4CED4", "#0077C0", "#C4CED4"],
        PHI: ["#006BB6", "#FFFFFF", "#006BB6", "#FFFFFF"],
        PHX: ["#1D1160", "#E56020"],
        POR: ["#000000", "#E03A3E"],
        SAC: ["#5A2D81", "#FFFFFF", "#9B5DD5", "#AF68F1"],
        SAS: ["#000000", "#C4CED4", "#000000", "#FFFFFF"],
        TOR: ["#CE1141", "#FFFFFF"],
        UTA: ["#002B5C", "#F9A01B", "#002B5C", "#F9A01B"],
        WAS: ["#002B5C", "#FFFFFF", "#0053BC"]
    };
    function N(e) {
        let t = A[e] || ["#F59E0B", "#000000"];
        return {
            bg: t[0],
            text: t[1],
            accent: t[2] ?? t[0]
        }
    }
    function B(e) {
        let t = e.replace("#", "");
        if (t.length < 6)
            return 0;
        let a = e => {
            let t = e / 255;
            return t <= .03928 ? t / 12.92 : Math.pow((t + .055) / 1.055, 2.4)
        }
        ;
        return .2126 * a(parseInt(t.slice(0, 2), 16)) + .7152 * a(parseInt(t.slice(2, 4), 16)) + .0722 * a(parseInt(t.slice(4, 6), 16))
    }
    function D(e, t=!1) {
        let a = A[e] || ["#F59E0B", "#000000"];
        if (t && a[3])
            return a[3];
        if (a[2])
            return a[2];
        let r = a[0]
          , n = a[1]
          , i = (e, t) => (Math.max(e, t) + .05) / (Math.min(e, t) + .05)
          , l = e => {
            let t = B(e);
            return Math.min(i(t, 1), i(t, .013))
        }
        ;
        return l(r) >= l(n) ? r : n
    }
    function v(e, t) {
        let a = B(e)
          , r = B(t);
        return (Math.max(a, r) + .05) / (Math.min(a, r) + .05) >= 2 ? t : a > .5 ? "#000000" : "#FFFFFF"
    }
    e.s(["getContrastingTextColor", () => v, "getReadableTeamColor", () => D, "getTeamColors", () => N], 17428)
}
, 89050, e => {
    "use strict";
    let t = [{
        min: 97,
        grade: "S",
        label: "GOAT",
        color: "#a855f7"
    }, {
        min: 91,
        grade: "A",
        label: "All-Time Great",
        color: "#22c55e"
    }, {
        min: 85,
        grade: "B",
        label: "Elite",
        color: "#3b82f6"
    }, {
        min: 78,
        grade: "C",
        label: "Solid",
        color: "#f59e0b"
    }, {
        min: 70,
        grade: "D",
        label: "Average",
        color: "#64748b"
    }, {
        min: 0,
        grade: "F",
        label: "Weak",
        color: "#ef4444"
    }]
      , a = .46
      , r = .25
      , n = .18
      , i = .07
      , l = .04
      , s = 133.4
      , o = 39.7
      , d = 29.3
      , p = 6.1
      , c = 3.2
      , g = {
        "1960s": {
            ppg: 30,
            rpg: 18,
            apg: 8,
            spg: 1.8,
            bpg: 1.8
        },
        "1970s": {
            ppg: 28,
            rpg: 13,
            apg: 9,
            spg: 2,
            bpg: 2
        },
        "1980s": {
            ppg: 28,
            rpg: 11,
            apg: 11,
            spg: 2.2,
            bpg: 2
        },
        "1990s": {
            ppg: 27,
            rpg: 11,
            apg: 9,
            spg: 2,
            bpg: 2
        },
        "2000s": {
            ppg: 27,
            rpg: 11,
            apg: 9,
            spg: 2,
            bpg: 2
        },
        "2010s": {
            ppg: 28,
            rpg: 11,
            apg: 9,
            spg: 1.8,
            bpg: 1.8
        },
        "2020s": {
            ppg: 28,
            rpg: 11,
            apg: 9,
            spg: 1.8,
            bpg: 1.8
        }
    }
      , u = {
        PG: {
            ppg: .4,
            rpg: .1,
            apg: .35,
            spg: .1,
            bpg: .05
        },
        SG: {
            ppg: .45,
            rpg: .1,
            apg: .2,
            spg: .2,
            bpg: .05
        },
        SF: {
            ppg: .45,
            rpg: .15,
            apg: .2,
            spg: .15,
            bpg: .05
        },
        PF: {
            ppg: .4,
            rpg: .3,
            apg: .1,
            spg: .1,
            bpg: .1
        },
        C: {
            ppg: .4,
            rpg: .35,
            apg: .1,
            spg: .05,
            bpg: .1
        }
    }
      , F = new Set(["larry bird", "tim duncan", "kevin durant", "magic johnson", "shaquille o'neal", "hakeem olajuwon", "bill russell", "kobe bryant", "oscar robertson", "karl malone", "kevin garnett", "isiah thomas", "tony parker", "manu ginobili", "draymond green", "scottie pippen", "dennis rodman", "stephen curry", "nikola jokic", "dirk nowitzki"]);
    function f(e, t=!1) {
        let a = t ? 1.25 : 1
          , r = g[e.decade || "2020s"] || g["2020s"]
          , n = 0;
        if (t) {
            let t = {
                ...u[e.positions?.[0] || e.pos || "SF"] || u.SF
            }
              , i = ["spg", "bpg"].filter(t => null === e[t] || void 0 === e[t] || isNaN(e[t]));
            if (i.length > 0) {
                let e = ["ppg", "rpg", "apg", "spg", "bpg"].filter(e => !i.includes(e)).reduce( (e, a) => e + t[a], 0)
                  , a = e > 0 ? 1 / e : 1;
                ["ppg", "rpg", "apg"].forEach(e => t[e] *= a),
                i.forEach(e => t[e] = 0)
            }
            ["ppg", "rpg", "apg", "spg", "bpg"].forEach(i => {
                let l = e[i];
                if (null != l && !isNaN(l)) {
                    let e = l / r[i];
                    e > 1 && (e = Math.pow(e, a)),
                    n += t[i] * e
                }
            }
            )
        } else
            ["ppg", "rpg", "apg", "spg", "bpg"].forEach(t => {
                let a = e[t];
                null == a || isNaN(a) || (n += a / r[t])
            }
            );
        let i = 60 + 40 * n
          , l = e.positions?.length || 1
          , s = 0;
        if (t) {
            let t = e.player?.toLowerCase() || "";
            s = 2.5 * !!F.has(t)
        }
        return Math.min(100, Math.round((i + (l - 1) * (t ? 3 : 2) + s) * 10) / 10)
    }
    function m(e) {
        return t.find(t => e >= t.min) || t[t.length - 1]
    }
    function b(e) {
        return h.find(t => e >= t.minWins) || h[h.length - 1]
    }
    let h = [{
        minWins: 80,
        grade: "S",
        label: "PERFECT",
        color: "#a855f7"
    }, {
        minWins: 72,
        grade: "A+",
        label: "HISTORIC",
        color: "#22c55e"
    }, {
        minWins: 62,
        grade: "A",
        label: "DYNASTY",
        color: "#22c55e"
    }, {
        minWins: 57,
        grade: "B",
        label: "CONTENDER",
        color: "#3b82f6"
    }, {
        minWins: 50,
        grade: "C",
        label: "PLAYOFF",
        color: "#f59e0b"
    }, {
        minWins: 40,
        grade: "D",
        label: "LOTTERY",
        color: "#64748b"
    }, {
        minWins: 0,
        grade: "F",
        label: "TANKING",
        color: "#ef4444"
    }];
    function C(e, t=!1) {
        return t ? function(e) {
            if (0 === e.length)
                return {
                    teamOvr: 0,
                    wins: 0,
                    losses: 82,
                    grade: "F",
                    label: "TANKING",
                    color: "#ef4444"
                };
            let t = e.map(e => f(e, !0))
              , a = Math.round(1.1 * Math.pow(t.reduce( (e, t) => e * t, 1), 1 / t.length) * 10) / 10
              , r = Math.round(82 * Math.pow(Math.min(a / 110, 1), 2.2))
              , n = h.find(e => r >= e.minWins) || h[h.length - 1];
            return {
                teamOvr: a,
                wins: r,
                losses: 82 - r,
                grade: n.grade,
                label: n.label,
                color: n.color
            }
        }(e) : function(e) {
            if (0 === e.length)
                return {
                    teamOvr: 0,
                    wins: 0,
                    losses: 82,
                    grade: "F",
                    label: "TANKING",
                    color: "#ef4444"
                };
            let {adjustedSpg: t, adjustedBpg: g} = A(e)
              , u = e.reduce( (e, t) => e + (t.ppg || 0), 0)
              , F = e.reduce( (e, t) => e + (t.rpg || 0), 0)
              , f = e.reduce( (e, t) => e + (t.apg || 0), 0)
              , m = Math.round(100 * (u / s * a + F / o * r + f / d * n + t / p * i + g / c * l) * 10) / 10
              , b = Math.round(82 * Math.pow(Math.min(m / 110, 1), 1.15))
              , C = h.find(e => b >= e.minWins) || h[h.length - 1];
            return {
                teamOvr: m,
                wins: b,
                losses: 82 - b,
                grade: C.grade,
                label: C.label,
                color: C.color
            }
        }(e)
    }
    function y(e, t=!1) {
        return C(e, t).teamOvr
    }
    function E(e) {
        return Math.round(82 * Math.pow(Math.min(e / 110, 1), 1.15))
    }
    function A(e) {
        let t = e.filter(e => e.spg > 0).map(e => e.spg)
          , a = e.filter(e => e.bpg > 0).map(e => e.bpg)
          , r = t.length
          , n = a.length;
        return {
            adjustedSpg: t.reduce( (e, t) => e + t, 0) * (r > 0 ? 5 / r : 1),
            adjustedBpg: a.reduce( (e, t) => e + t, 0) * (n > 0 ? 5 / n : 1)
        }
    }
    e.s(["adjustSpgBpg", () => A, "calculatePlayerRating", () => f, "calculateTeamRating", () => y, "calculateTeamResult", () => C, "getGrade", () => m, "getTeamGradeFromWins", () => b, "projectedWins", () => E])
}
, 70065, e => {
    "use strict";
    var t = e.i(68866)
      , a = e.i(47163);
    function r({className: e, ...r}) {
        return (0,
        t.jsx)("div", {
            "data-slot": "card",
            className: (0,
            a.cn)("bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm", e),
            ...r
        })
    }
    function n({className: e, ...r}) {
        return (0,
        t.jsx)("div", {
            "data-slot": "card-header",
            className: (0,
            a.cn)("@container/card-header grid auto-rows-min grid-rows-[auto_auto] items-start gap-2 px-6 has-data-[slot=card-action]:grid-cols-[1fr_auto] [.border-b]:pb-6", e),
            ...r
        })
    }
    function i({className: e, ...r}) {
        return (0,
        t.jsx)("div", {
            "data-slot": "card-title",
            className: (0,
            a.cn)("leading-none font-semibold", e),
            ...r
        })
    }
    function l({className: e, ...r}) {
        return (0,
        t.jsx)("div", {
            "data-slot": "card-description",
            className: (0,
            a.cn)("text-muted-foreground text-sm", e),
            ...r
        })
    }
    function s({className: e, ...r}) {
        return (0,
        t.jsx)("div", {
            "data-slot": "card-content",
            className: (0,
            a.cn)("px-6", e),
            ...r
        })
    }
    e.s(["Card", () => r, "CardContent", () => s, "CardDescription", () => l, "CardHeader", () => n, "CardTitle", () => i])
}
, 62452, (e, t, a) => {
    t.exports = e.r(32330)
}
, 90768, e => {
    "use strict";
    let t = (0,
    e.i(10965).default)("LoaderCircle", [["path", {
        d: "M21 12a9 9 0 1 1-6.219-8.56",
        key: "13zald"
    }]]);
    e.s(["Loader2", () => t], 90768)
}
, 42838, e => {
    "use strict";
    let t = (0,
    e.i(10965).default)("Shield", [["path", {
        d: "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z",
        key: "oel41y"
    }]]);
    e.s(["Shield", () => t], 42838)
}
]);
