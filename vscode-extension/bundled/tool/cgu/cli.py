"""
CGU CLI

命令列介面
"""

import argparse
import asyncio
import json
import sys

from cgu.core import (
    METHOD_CONFIGS,
    CreativityLevel,
    select_method_for_task,
)


def cmd_generate(args):
    """生成創意點子"""
    from cgu.server import generate_ideas

    result = asyncio.run(
        generate_ideas(
            topic=args.topic,
            creativity_level=args.level,
            count=args.count,
            constraints=args.constraints,
        )
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_spark(args):
    """概念碰撞"""
    from cgu.server import spark_collision

    result = asyncio.run(
        spark_collision(
            concept_a=args.concept_a,
            concept_b=args.concept_b,
        )
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_expand(args):
    """聯想擴展"""
    from cgu.server import associative_expansion

    result = asyncio.run(
        associative_expansion(
            seed=args.seed,
            direction=args.direction,
            depth=args.depth,
        )
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_apply(args):
    """應用創意方法"""
    from cgu.server import apply_method

    result = asyncio.run(
        apply_method(
            method=args.method,
            input_concept=args.input,
            options=None,
        )
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_list_methods(args):
    """列出所有方法"""
    print("\n🎨 CGU 創意方法列表\n")
    print("=" * 60)

    current_category = None
    for method, config in METHOD_CONFIGS.items():
        if config.category.value != current_category:
            current_category = config.category.value
            print(f"\n📁 {current_category.upper()}")
            print("-" * 40)

        speed_icon = "⚡" if config.thinking_speed == "fast" else "🐢"
        levels = ",".join(map(str, config.suitable_levels))
        print(f"  {speed_icon} {method.value:<20} L{levels:<6} {config.description}")

    print("\n" + "=" * 60)
    print(f"共 {len(METHOD_CONFIGS)} 種方法")


def cmd_recommend(args):
    """推薦方法"""
    level = CreativityLevel(args.level)
    method = select_method_for_task(
        creativity_level=level,
        prefer_fast=args.fast,
        is_stuck=args.stuck,
        purpose=args.purpose,
    )

    config = METHOD_CONFIGS.get(method)

    print(f"\n🎯 推薦方法: {method.value}")
    if config:
        print(f"   描述: {config.description}")
        print(f"   類別: {config.category.value}")
        print(f"   速度: {'⚡ 快' if config.thinking_speed == 'fast' else '🐢 慢'}")
        print(f"   策略: {config.agent_strategy}")


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="cgu",
        description="🎨 Creativity Generation Unit - 創意發想工具",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # generate 命令
    p_generate = subparsers.add_parser("generate", help="生成創意點子")
    p_generate.add_argument("topic", help="發想主題")
    p_generate.add_argument(
        "-l",
        "--level",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="創意層級 (1=組合, 2=探索, 3=變革)",
    )
    p_generate.add_argument("-c", "--count", type=int, default=5, help="點子數量")
    p_generate.add_argument("--constraints", nargs="*", help="限制條件")
    p_generate.set_defaults(func=cmd_generate)

    # spark 命令
    p_spark = subparsers.add_parser("spark", help="概念碰撞")
    p_spark.add_argument("concept_a", help="概念 A")
    p_spark.add_argument("concept_b", help="概念 B")
    p_spark.set_defaults(func=cmd_spark)

    # expand 命令
    p_expand = subparsers.add_parser("expand", help="聯想擴展")
    p_expand.add_argument("seed", help="種子概念")
    p_expand.add_argument(
        "-d",
        "--direction",
        default="similar",
        choices=["similar", "opposite", "random", "cross-domain"],
        help="擴展方向",
    )
    p_expand.add_argument("--depth", type=int, default=2, help="擴展深度")
    p_expand.set_defaults(func=cmd_expand)

    # apply 命令
    p_apply = subparsers.add_parser("apply", help="應用創意方法")
    p_apply.add_argument("method", help="方法名稱")
    p_apply.add_argument("input", help="輸入概念")
    p_apply.set_defaults(func=cmd_apply)

    # methods 命令
    p_methods = subparsers.add_parser("methods", help="列出所有方法")
    p_methods.set_defaults(func=cmd_list_methods)

    # recommend 命令
    p_recommend = subparsers.add_parser("recommend", help="推薦創意方法")
    p_recommend.add_argument(
        "-l", "--level", type=int, default=1, choices=[1, 2, 3], help="創意層級"
    )
    p_recommend.add_argument("--fast", action="store_true", default=True, help="偏好快速方法")
    p_recommend.add_argument("--slow", action="store_true", help="偏好慢速方法")
    p_recommend.add_argument("--stuck", action="store_true", help="卡關中")
    p_recommend.add_argument("-p", "--purpose", help="目的")
    p_recommend.set_defaults(func=cmd_recommend)

    # 解析參數
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # 處理 --slow 覆蓋 --fast
    if hasattr(args, "slow") and args.slow:
        args.fast = False

    # 執行命令
    args.func(args)


if __name__ == "__main__":
    main()
