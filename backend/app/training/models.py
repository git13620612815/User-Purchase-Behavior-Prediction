"""HeteroSAGE 为在线模型。GCN、GAT 只用于同质投影上的离线对比。"""

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import Tensor, nn
from torch_geometric.nn import GATConv, GCNConv, SAGEConv
from torch_geometric.utils import scatter


def normalize_edge_weight(edge_index: Tensor, edge_weight: Tensor, num_dst: int) -> Tensor:
    dest = edge_index[1]
    denom = scatter(edge_weight, dest, dim=0, dim_size=num_dst, reduce="sum").clamp(min=1e-8)
    return edge_weight / denom[dest]


class WeightedSAGEConv(SAGEConv):
    """带边权的 GraphSAGE。权重先按目标节点归一化，再用求和聚合，得到加权平均。"""

    def forward(self, x, edge_index, edge_weight=None):
        if isinstance(x, Tensor):
            x = (x, x)
        src, dst = x
        if edge_weight is None or edge_index.numel() == 0:
            out = self.propagate(edge_index, x=x, size=(src.size(0), dst.size(0)))
        else:
            weight = normalize_edge_weight(edge_index, edge_weight.view(-1), dst.size(0))
            messages = src[edge_index[0]] * weight.view(-1, 1)
            out = scatter(messages, edge_index[1], dim=0, dim_size=dst.size(0), reduce="sum")
        out = self.lin_l(out)
        if self.root_weight and dst is not None:
            out = out + self.lin_r(dst)
        if self.normalize:
            out = F.normalize(out, p=2.0, dim=-1)
        return out


class HeteroSAGE(nn.Module):
    def __init__(self, user_dim: int, product_dim: int, category_dim: int, hidden: int = 64, out_dim: int = 64, dropout: float = 0.3):
        super().__init__()
        self.dropout = dropout
        self.hidden = hidden
        self.out_dim = out_dim
        rels = (
            ("user", "behavior", "product"),
            ("product", "rev_behavior", "user"),
            ("product", "belong", "category"),
            ("category", "rev_belong", "product"),
        )
        self.rels = rels
        self.conv1 = nn.ModuleDict({
            _key(rel): WeightedSAGEConv(_in_dims(rel, user_dim, product_dim, category_dim), hidden, aggr="sum")
            for rel in rels
        })
        self.conv2 = nn.ModuleDict({
            _key(rel): WeightedSAGEConv((hidden, hidden), out_dim, aggr="sum")
            for rel in rels
        })
        self.fall1 = nn.ModuleDict({
            "user": nn.Linear(user_dim, hidden),
            "product": nn.Linear(product_dim, hidden),
            "category": nn.Linear(category_dim, hidden),
        })
        self.fall2 = nn.ModuleDict({
            "user": nn.Linear(hidden, out_dim),
            "product": nn.Linear(hidden, out_dim),
            "category": nn.Linear(hidden, out_dim),
        })

    def forward(self, x_dict, edge_index_dict, edge_weight_dict, edge_index_dict2=None, edge_weight_dict2=None):
        hidden = self._apply(self.conv1, self.fall1, x_dict, edge_index_dict, edge_weight_dict, self.hidden)
        hidden = {key: F.dropout(F.relu(value), p=self.dropout, training=self.training) for key, value in hidden.items()}
        # 输出向量不做 ReLU，点积才可能得到小于 0.5 的购买概率
        second_edges = edge_index_dict if edge_index_dict2 is None else edge_index_dict2
        second_weights = edge_weight_dict if edge_weight_dict2 is None else edge_weight_dict2
        out = self._apply(self.conv2, self.fall2, hidden, second_edges, second_weights, self.out_dim)
        out = {key: F.dropout(value, p=self.dropout, training=self.training) for key, value in out.items()}
        return out

    def _apply(self, convs, fallback, x_dict, edge_index_dict, edge_weight_dict, width: int):
        buckets: dict[str, list[Tensor]] = {key: [] for key in x_dict}
        for rel in self.rels:
            edge_index = edge_index_dict.get(rel)
            if edge_index is None or edge_index.numel() == 0:
                continue
            src, _, dst = rel
            weight = edge_weight_dict.get(rel)
            buckets[dst].append(convs[_key(rel)]((x_dict[src], x_dict[dst]), edge_index, weight))
        result = {}
        for ntype, features in x_dict.items():
            parts = buckets.get(ntype) or []
            if parts:
                stacked = parts[0]
                for extra in parts[1:]:
                    stacked = stacked + extra
                result[ntype] = stacked
            else:
                result[ntype] = fallback[ntype](features)
        return result


def _key(rel: tuple[str, str, str]) -> str:
    return "__".join(rel)


def _in_dims(rel, user_dim, product_dim, category_dim):
    dims = {"user": user_dim, "product": product_dim, "category": category_dim}
    src, _, dst = rel
    return (dims[src], dims[dst])


class HomoEncoder(nn.Module):
    def __init__(self, user_dim: int, product_dim: int, hidden: int = 64, out_dim: int = 64, dropout: float = 0.3, kind: str = "GCN"):
        super().__init__()
        self.dropout = dropout
        self.kind = kind
        self.user_lin = nn.Linear(user_dim, hidden)
        self.product_lin = nn.Linear(product_dim, hidden)
        if kind == "GCN":
            self.conv1 = GCNConv(hidden, hidden)
            self.conv2 = GCNConv(hidden, out_dim)
            self.proj = None
        else:
            self.conv1 = GATConv(hidden, hidden, heads=4, concat=True, dropout=dropout)
            self.mid = nn.Linear(hidden * 4, hidden)
            self.conv2 = GATConv(hidden, hidden, heads=4, concat=True, dropout=dropout)
            self.proj = nn.Linear(hidden * 4, out_dim)

    def forward(self, user_x, product_x, edge_index, edge_weight=None):
        user_h = self.user_lin(user_x)
        product_h = self.product_lin(product_x)
        x = torch.cat([user_h, product_h], dim=0)
        if self.kind == "GCN":
            h = F.relu(self.conv1(x, edge_index, edge_weight))
            h = F.dropout(h, p=self.dropout, training=self.training)
            out = self.conv2(h, edge_index, edge_weight)
        else:
            h = F.relu(self.mid(self.conv1(x, edge_index)))
            h = F.dropout(h, p=self.dropout, training=self.training)
            out = self.proj(self.conv2(h, edge_index))
        out = F.dropout(out, p=self.dropout, training=self.training)
        n_user = user_x.size(0)
        return out[:n_user], out[n_user:]
