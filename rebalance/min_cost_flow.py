class MinCostFlow:
    """基于贪心近似的最小成本流求解器（V0.2 简化版实现）"""
    
    @staticmethod
    def solve(source_supplies, target_demands, cost_matrix):
        """
        source_supplies: {src_region: available_cars}
        target_demands: {dst_region: needed_cars}
        cost_matrix: {(src, dst): time_cost}
        返回: 调度指令列表 [(src, dst, count)]
        """
        instructions = []
        
        # 将所有可能的边按成本从小到大排序
        edges = sorted(cost_matrix.items(), key=lambda x: x[1])
        
        # 贪心匹配：优先满足成本最小的区域对
        for (src, dst), cost in edges:
            if cost == float('inf'):
                continue
                
            if source_supplies.get(src, 0) > 0 and target_demands.get(dst, 0) > 0:
                # 能调度的数量是供给和需求的最小值
                flow = min(source_supplies[src], target_demands[dst])
                instructions.append((src, dst, flow))
                
                # 更新剩余供需
                source_supplies[src] -= flow
                target_demands[dst] -= flow
                
        return instructions
