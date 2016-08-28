let global = this;
function load_tables(tables, finished) {
    let load_tables = {};
    let num_loaded = 0;
    for (let name of tables) {
        let close_name = name;
        d3.json("data/" + name + ".json", function (data) {
            global[close_name] = data;
            load_tables[close_name] = data;
            if (++num_loaded == tables.length)
                finished(load_tables);
        });
    }
}
function load_data() {
    d3.json("data/l10n.json", function (l10n) {
        return d3.json("data/technology.json", process_tree);
    });
}

function get_tier(techs, tech) {
    if ('tier' in tech)
        return tech['tier'];
    if (tech.prerequisites.length == 0)
        return tech.tier = 0;
    return tech.tier = 1 + d3.max(tech.prerequisites, t => get_tier(techs, techs[t]));
}

function translate(category, name) {
    let table = l10n[category];
    if (name in table)
        return table[name];
    if (/-[0-9]*$/.exec(name)) {
        let base = name.substring(0, name.lastIndexOf('-'));
        return table[base] + ' ' + name.substring(name.lastIndexOf('-') + 1);
    }

    return name;
}

function process_tree(data) {
    let techs = data['technology'];
    let l10n = data['l10n'];
    let items = data['full-item'];

    // Clear the existing contents
    let tech_tree = document.getElementById("tech-tree");
    tech_tree.innerHTML = '';

    let svg_layer = document.createElementNS("http://www.w3.org/2000/svg",
      "svg");
    tech_tree.appendChild(svg_layer);

    // Lay out the nodes in the graph.
    let edges = sugiyama(
        Object.keys(techs).map(t => (get_tier(techs, techs[t]), techs[t])),
        t => t.prerequisites.map(t => techs[t]));

    // Make the techs, and shove each tier into its own column.
    let columns = [];
    for (let tech in techs) {
        let tier = get_tier(techs, techs[tech]);
        let cell = make_node(techs[tech], l10n, items);
        cell.y = techs[tech].y;
        if (!columns[tier]) {
            columns[tier] = [];
            columns[tier].order = tier;
        }
        columns[tier].push(cell);
    }

    // Create rows for each rank
    for (let col of columns) {
        let rows = col.rows = [];
        for (let cell of col)
            rows[cell.y] = cell;
    }

    // Turn the grid into a table.
    let table = document.createElement("table");
    tech_tree.appendChild(table);
    let nRows = d3.max(columns, col => col.rows.length);
    for (let y = 0; y < nRows; y++) {
        let row = document.createElement("tr");
        table.appendChild(row);
        for (let x = 0; x < columns.length; x++) {
            if (columns[x].rows[y])
                row.appendChild(columns[x].rows[y])
            else {
                let cell = document.createElement("td");
                row.appendChild(cell);
            }
        }
    }
    svg_layer.setAttribute("width", table.getBoundingClientRect().width);
    svg_layer.setAttribute("height", table.getBoundingClientRect().height);

    // Add in the edge splines
    let offsetX = tech_tree.getBoundingClientRect().left,
        offsetY = tech_tree.getBoundingClientRect().top;
    let lines = d3.select("svg")
        .selectAll("path")
        .data(edges)
        .enter().append("path");
    lines.attr("d", function (edge) {
        function y(el) {
            let rect = el.getBoundingClientRect();
            return (rect.top + rect.bottom) / 2 - offsetY;
        }
        function x(el, edge) {
            let rect = el.getBoundingClientRect();
            return rect[edge] - offsetX;
        }
        function coords(el, edge) {
            return x(el, edge) + ", " + y(el);
        }
        var str = "M " + coords(document.getElementById(edge.head.name), "right");
        let tier = edge.head.tier + 1;
        for (let interior_rank of edge.interior) {
            while (interior_rank >= table.children.length) {
                let row = document.createElement("tr");
                table.appendChild(row);
                for (let x = 0; x < columns.length; x++) {
                    let cell = document.createElement("td");
                    row.appendChild(cell);
                }
            }
            var el = table.children[interior_rank].children[tier++];
            str += " L " + coords(el, "left") + " L " + coords(el, "right");
        }
        str += " L " + coords(document.getElementById(edge.tail.name), "left");
        return str;
    });
    /*
    // Create the lines to match techs
    let prereqs = [];
    for (let tech in techs) {
        for (let prereq of techs[tech].prerequisites)
            prereqs.push({head: techs[prereq], tail: techs[tech]});
    }
    let offsetX = tech_tree.getBoundingClientRect().left,
        offsetY = tech_tree.getBoundingClientRect().top;
    let lines = d3.select("svg")
        .selectAll("line")
        .data(prereqs)
        .enter().append("line");
    lines.attr("x1", function (val) {
        let rect = document.getElementById(val.head.name).getBoundingClientRect();
        return rect.right - offsetX;
    }).attr("x2", function (val) {
        let rect = document.getElementById(val.tail.name).getBoundingClientRect();
        return rect.left - offsetX;
    }).attr("y1", function (val) {
        let rect = document.getElementById(val.head.name).getBoundingClientRect();
        return (rect.top + rect.bottom) / 2 - offsetY;
    }).attr("y2", function (val) {
        let rect = document.getElementById(val.tail.name).getBoundingClientRect();
        return (rect.top + rect.bottom) / 2 - offsetY;
    });*/
}

function sugiyama(nodes, edge_fn) {
    let rank = t => t.tier;
    // Make dummy nodes so that each edge crosses a single layer.
    let dummies = [];
    let parents = new Map();
    for (let n of nodes) {
        parents.set(n, edge_fn(n).map(function (pred) {
            let real_head = pred;
            while (rank(n) - rank(pred) > 1) {
                let dummy = { real_head: real_head, real_tail: n, tier:
                    rank(pred) + 1};
                parents.set(dummy, [pred]);
                pred = dummy;
                dummies.push(dummy);
            }
            return pred;
        }));
    }

    // Get a list of nodes in each rank.
    let ranks = [];
    for (let n of nodes) {
        if (!ranks[rank(n)])
            ranks[rank(n)] = [];
        ranks[rank(n)].push(n);
    }
    for (let n of dummies) {
        ranks[rank(n)].push(n);
    }

    // rank_edges[i] = list of edges from rank[i - 1] to rank[i]
    var rank_edges = [];
    for (let rank of ranks) {
        let edges = [];
        for (let n of rank) {
            edges = d3.merge([edges, parents.get(n).map(h => [h, n])]);
        }
        rank_edges.push(edges);
    }

    function count_crossings(order) {
        // The basic algorithm for counting edge crossings in a bipartite graph
        // is to sort the edges by the order of their start nodes/end nodes, and
        // count the number of inversions in the resulting order of end nodes.
        var crosscount = 0;
        for (var i = 1; i < ranks.length; i++) {
            var end = ranks[i];
            // Sort the edges.
            var edges = rank_edges[i];
            edges.sort(function (a, b) {
                if (a[0] == b[0])
                    return order.get(a[1]) - order.get(b[1]);
                return order.get(a[0]) - order.get(b[0]);
            });

            // Algorithm taken from <http://jgaa.info/accepted/2004/BarthMutzelJuenger2004.8.2.pdf>. I don't pretend to understand this; it could be optimized
            // better, probably.
            var firstindex = 1;
            while (firstindex < end.length) firstindex *= 2;
            var treesize = 2 * firstindex - 1;
            firstindex -= 1;
            var tree = [];
            for (var i = 0; i < treesize; i++) tree[i] = 0;
            for (var e of edges) {
                var index = order.get(e[1]) + firstindex;
                tree[index]++;
                while (index > 0) {
                    if (index % 2) crosscount += tree[index + 1];
                    index = Math.floor((index - 1) / 2);
                    tree[index]++;
                }
            }
        }

        return crosscount;
    }

    // Iterate through all the layers, sorting nodes by the mean position of
    // their parent nodes.
    function minimize_crossing(order, up) {
        var new_order = new Map();
        if (!up) {
            ranks.reverse();
            rank_edges.reverse();
        }
        for (var node of ranks[0])
            new_order.set(node, order.get(node));
        for (var i = 1; i < ranks.length; i++) {
            var edges = rank_edges[i - (1 - up)];
            var nodes = ranks[i];
            var adjacency = new Map(nodes.map(t => [t, []]));
            for (var e of edges) {
                adjacency.get(e[up + 0]).push(order.get(e[1 - up]));
            }
            var measure = new Map();
            for (var [node, arr] of adjacency.entries())
                measure.set(node, d3.mean(arr));
            nodes.sort(function (a, b) {
                return measure.get(a) - measure.get(b);
            });
            nodes.forEach((d, i) => new_order.set(d, i));
        }
        if (!up) {
            ranks.reverse();
            rank_edges.reverse();
        }
        return new_order;
    }

    // Set an initial order. XXX: DFS/BFS is a better order.
    var order = new Map();
    for (let rank of ranks) {
        rank.forEach((n, i) => order.set(n, i));
    }

    // Main loop of the algorithm.
    var best = order, bestcc = count_crossings(order);
    console.log("New crossing count: ", bestcc);
    for (var i = 0; i < 20; i++) {
        order = minimize_crossing(order, i % 2 == 0);
        var cc = count_crossings(order);
        console.log("New crossing count: ", cc);
        if (cc < bestcc) {
            best = order;
            bestcc = cc;
        }
    }

    // Insert the y values onto each of the nodes.
    for (let [node, y] of best.entries()) {
        node.y = y;
    }

    // Compute the spline parameters for each edge.
    var edge_splines = [];
    for (var i = 1; i < rank_edges.length; i++) {
        var edges = rank_edges[i];
        for (var edge of edges) {
            if (edge[0].real_tail || edge[1].real_tail) {
                if (edge[0].real_tail != edge[1])
                    continue;
                let interior = [];
                let dummy = edge[0];
                for (let dummy = edge[0]; dummy != edge[0].real_head;
                        dummy = parents.get(dummy)[0])
                    interior.push(dummy.y);
                interior.reverse();
                edge_splines.push({
                    head: edge[0].real_head,
                    tail: edge[1],
                    interior: interior
                });
            } else {
                edge_splines.push({
                    head: edge[0],
                    tail: edge[1],
                    interior: []
                });
            }
        }
    }
    return edge_splines;
}

function make_node(tech, l10n, item_dict) {
    let node = document.createElement("td");
    node.className = 'tech';
    node.id = tech.name;

    let icon = document.createElement("img");
    icon.className = 'tech-icon';
    icon.src = "image/" + tech.icon;
    node.appendChild(icon);

    let text = document.createElement("div");
    text.textContent = translate('technology-name', tech.name);
    node.appendChild(text);

    let timeText = document.createElement("div");
    timeText.appendChild(document.createTextNode(tech.unit.count + "×"));
    let clock = document.createElement("img");
    clock.src = "image/__core__/graphics/clock-icon.png";
    timeText.appendChild(clock);
    timeText.appendChild(document.createTextNode(tech.unit.time));

    for (let [pack, count] of tech.unit.ingredients) {
        let image = document.createElement("img");
        image.src = "image/" + item_dict[pack].icon;
        image.title = l10n['item-name'][pack];
        timeText.appendChild(image);
        timeText.appendChild(document.createTextNode(count + " "));
    }

    node.appendChild(timeText);
    return node;
}
