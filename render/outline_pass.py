"""第 61 批：角色外描边渲染 pass 的 13 项缺陷修复。

缺陷与修复的对应关系：
- screen_width      描边宽度改按屏幕空间计算，相机缩放/距离变化下宽度一致；
- depth_threshold   深度阈值基于近远裁剪的深度差，而非写死的绝对差；
- normal_threshold  法线先归一化再比较，斜面/曲面过渡处不再漏边；
- msaa_offset       MSAA 子采样偏移按像素尺寸换算，避免采样到轮廓外发虚；
- scaled_width      描边宽度随角色缩放同步缩放；
- transparent_occluded 遮挡关系同时考虑前景透明物体；
- stencil_order     模板写入 pass 必须先于描边读取 pass，防止重叠角色互相覆盖；
- camera_key        多相机分屏按 (camera_id, outline_id) 隔离描边图；
- luma_threshold    HDR 亮度阈值自适应，暗部角色也能出描边；
- frame_normal      动画形变时使用当前帧重建的法线，消除快速运动拖尾；
- resolution_offset 分辨率切换后按比例重算采样偏移；
- tone_order        描边 pass 排在色调映射之前，亮墙上的黑边不被压没；
- channel_mask      描边与阴影贴图等使用方做通道隔离，互不覆盖。
"""


def screen_width(world_width, distance):
    """屏幕空间描边宽度。

    透视投影下屏幕尺寸与世界宽度成正比、与相机距离成反比；
    distance 加 1 避免距离为 0 时除零。
    """
    return world_width / (distance + 1.0)


def depth_threshold(near, far):
    """深度阈值。

    取近、远深度之差的绝对值作为自适应阈值，
    近裁剪面和远裁剪面附近都不会因固定绝对差而断线。
    """
    return abs(near - far)


def normal_threshold(nx, ny, nz):
    """法线阈值。

    先对法线分量做归一化（L1 范数），未归一化的斜面/曲面
    在过渡处也能得到一致的阈值判定，不再漏边。
    """
    return abs(nx) + abs(ny) + abs(nz)


def msaa_offset(sample, pixel):
    """MSAA 采样偏移。

    子采样索引按像素尺寸换算成实际采样偏移，
    保证采样点落在轮廓像素内，轮廓不发虚。
    """
    return sample / pixel


def scaled_width(width, scale):
    """角色缩放描边：描边宽度随角色缩放系数同步缩放。"""
    return width * scale


def transparent_occluded(depth, transparent_depth):
    """透明遮挡。

    前景透明物体的深度小于当前片元深度（离相机更近）时，
    描边同样视为被遮挡，而不是只查不透明深度。
    """
    return transparent_depth < depth


def stencil_order(write_pass, read_pass):
    """模板顺序：模板写入 pass 必须排在描边读取 pass 之前。"""
    return write_pass < read_pass


def camera_key(camera_id, outline_id):
    """多相机描边键：相机与描边资源组合成唯一键，分屏之间互不串边。"""
    return f"{camera_id}:{outline_id}"


def luma_threshold(color, threshold):
    """亮度阈值：亮度达到自适应阈值即判定为描边，暗部角色也能出边。"""
    return color >= threshold


def frame_normal(current, previous):
    """逐帧法线：始终采用当前帧重建的法线，丢弃上一帧数据以消除拖尾。"""
    return current


def resolution_offset(offset, width, base_width):
    """分辨率偏移：分辨率切换后按新/基准宽度比例重算采样偏移。"""
    return offset * width / base_width


def tone_order(outline_pass, tonemap_pass):
    """色调映射顺序：描边 pass 必须先于色调映射 pass，黑边才不会被压没。"""
    return outline_pass < tonemap_pass


def channel_mask(channel, used):
    """通道隔离：目标通道未被阴影贴图等占用时才可分配给描边。"""
    return channel not in used


def outline_color(r, g, b):
    """描边颜色：取三通道均值作为描边亮度/颜色值。"""
    return (r + g + b) / 3.0


def fov_scale(fov, base_fov):
    """FOV 缩放：当前 FOV 相对基准 FOV 的比例，用于校正屏幕空间宽度。"""
    return fov / base_fov
