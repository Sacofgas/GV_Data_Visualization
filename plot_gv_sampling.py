import polars as pl
from argparse import ArgumentParser, Namespace
from json import dumps as json_dumps
from pathlib import Path
from webbrowser import open_new_tab as wb_open_new_tab

from bokeh.embed import file_html
from bokeh.layouts import column
from bokeh.models import Column, ColumnDataSource
from bokeh.models import Legend  # type: ignore [attr-defined]
from bokeh.plotting import figure
from bokeh.resources import CDN


###################
#    CONSTANTS    #
###################

# Data
CSV_DATA_FILE_NAME = 'data.csv'
SCHEMA = pl.Schema(
    {
        'unix_time': pl.Float64,
        'vg_m3': pl.Float64,
        'vm_m3': pl.Float64,
        'vb_m3': pl.Float64,
        'pulses_reed_1': pl.Int64,
        'pulses_reed_2': pl.Int64,
        'q_m3h': pl.Float64,
    }
)
NULL_VALUES = json_dumps(None)

# Plot
WIDTH = 1000
HEIGHT = 400
PLOT_HTML_FILE_NAME = 'plot.html'


###################
#    FUNCTIONS    #
###################

def _are_series_data_unique(series: pl.Series) -> bool:
    return series.n_unique() == len(series)


def validate_unix_time_data(unix_times: pl.Series) -> None:
    if not _are_series_data_unique(unix_times):
        raise ValueError(f'UNIX time are not unique.')
    elif not unix_times.is_sorted():
        raise ValueError(f'UNIX times are not monotonically increasing.')
    dt = unix_times.diff()
    dt_avg = dt.mean()
    dt_std = dt.std()
    assert isinstance(dt_avg, float)  # for MyPy
    assert isinstance(dt_std, float)  # for MyPy
    dt_std_over_avg = dt_std / dt_avg
    print(
        f'{dt_avg = }\n'
        f'{dt_std = }\n'
        f'{dt_std_over_avg = }\n'
    )


def get_df(gv_sampling_dir_path: Path | str) -> pl.DataFrame:
    # get data
    csv_data_file_path = Path(gv_sampling_dir_path) / CSV_DATA_FILE_NAME
    df = pl.read_csv(csv_data_file_path, schema=SCHEMA, null_values=NULL_VALUES)
    # handle time data
    validate_unix_time_data(df['unix_time'])
    df = df.with_columns(
        sample_index=pl.arange(len(df)),
        time_s=pl.col('unix_time') - pl.col('unix_time').min(),
        delta_time_s=pl.col('unix_time').diff(),
    )
    df = df.drop('unix_time')
    # create delta and cumulative columns
    df = df.with_columns(
        delta_vg_m3=pl.col('vg_m3').diff(),
        delta_vm_m3=pl.col('vm_m3').diff(),
        delta_vb_m3=pl.col('vb_m3').diff(),
        delta_pulses_reed_1=pl.col('pulses_reed_1').diff(),
        delta_pulses_reed_2=pl.col('pulses_reed_2').diff(),
        integral_q_m3=(pl.col('q_m3h') / 3600.0 * pl.col('delta_time_s')).cum_sum(),
    )
    # reorder columns
    df = df.select(
        'sample_index', 'time_s', 'delta_time_s',
        'vg_m3', 'vm_m3', 'vb_m3', 'delta_vg_m3', 'delta_vm_m3', 'delta_vb_m3',
        'pulses_reed_1', 'pulses_reed_2', 'delta_pulses_reed_1', 'delta_pulses_reed_2',
        'integral_q_m3', 'q_m3h',
    )
    # return dataframe
    return df


def create_column_plot(df: pl.DataFrame) -> Column:
    # create column data source
    cds = ColumnDataSource(df)

    # plot of time delta
    fig_dt = figure(title='Time delta', x_axis_label='Time (s)', y_axis_label='Time interval (s)', width=WIDTH, height=HEIGHT, toolbar_location='above')  # type: ignore [call-arg]
    fig_dt.scatter('time_s', 'delta_time_s', source=cds, color='black')
    fig_dt.line(   'time_s', 'delta_time_s', source=cds, color='black')
    assert hasattr(fig_dt.y_range, 'start')  # for MyPy
    fig_dt.y_range.start = 0.0

    # plot of volumes
    fig_v = figure(title='Volumes', x_axis_label='Time (s)', y_axis_label='Volume (m^3)', width=WIDTH, height=HEIGHT, toolbar_location='above')  # type: ignore [call-arg]
    fig_v.add_layout(Legend(), 'right')
    fig_v.legend.click_policy = 'hide'
    fig_v.scatter('time_s', 'vg_m3', source=cds, legend_label='Vg', color='red')
    fig_v.scatter('time_s', 'vm_m3', source=cds, legend_label='Vm', color='green')
    fig_v.scatter('time_s', 'vb_m3', source=cds, legend_label='Vb', color='blue')
    fig_v.line(   'time_s', 'vg_m3', source=cds, legend_label='Vg', color='red')
    fig_v.line(   'time_s', 'vm_m3', source=cds, legend_label='Vm', color='green')
    fig_v.line(   'time_s', 'vb_m3', source=cds, legend_label='Vb', color='blue')

    # plot of delta volumes
    fig_dv = figure(title='Delta volumes', x_axis_label='Time (s)', y_axis_label='Delta volume (m^3)', width=WIDTH, height=HEIGHT, toolbar_location='above')  # type: ignore [call-arg]
    fig_dv.add_layout(Legend(), 'right')
    fig_dv.legend.click_policy = 'hide'
    fig_dv.scatter('time_s', 'delta_vg_m3', source=cds, legend_label='delta Vg', color='red')
    fig_dv.scatter('time_s', 'delta_vm_m3', source=cds, legend_label='delta Vm', color='green')
    fig_dv.scatter('time_s', 'delta_vb_m3', source=cds, legend_label='delta Vb', color='blue')
    fig_dv.line(   'time_s', 'delta_vg_m3', source=cds, legend_label='delta Vg', color='red')
    fig_dv.line(   'time_s', 'delta_vm_m3', source=cds, legend_label='delta Vm', color='green')
    fig_dv.line(   'time_s', 'delta_vb_m3', source=cds, legend_label='delta Vb', color='blue')

    # plot of reeds counts
    fig_rc = figure(title='Reeds counts', x_axis_label='Time (s)', y_axis_label='Counts (adim. natural)', width=WIDTH, height=HEIGHT, toolbar_location='above')  # type: ignore [call-arg]
    fig_rc.add_layout(Legend(), 'right')
    fig_rc.legend.click_policy = 'hide'
    fig_rc.scatter('time_s', 'pulses_reed_1', source=cds, legend_label='reed 1', color='crimson', marker='triangle', size=6)
    fig_rc.scatter('time_s', 'pulses_reed_2', source=cds, legend_label='reed 2', color='maroon',  marker='inverted_triangle', size=6)
    fig_rc.line(   'time_s', 'pulses_reed_1', source=cds, legend_label='reed 1', color='crimson')
    fig_rc.line(   'time_s', 'pulses_reed_2', source=cds, legend_label='reed 2', color='maroon')

    # plot of delta reeds counts
    fig_drc = figure(title='Delta reeds counts', x_axis_label='Time (s)', y_axis_label='Delta counts (adim. natural)', width=WIDTH, height=HEIGHT, toolbar_location='above')  # type: ignore [call-arg]
    fig_drc.add_layout(Legend(), 'right')
    fig_drc.legend.click_policy = 'hide'
    fig_drc.scatter('time_s', 'delta_pulses_reed_1', source=cds, legend_label='delta reed 1', color='crimson', marker='triangle', size=6)
    fig_drc.scatter('time_s', 'delta_pulses_reed_2', source=cds, legend_label='delta reed 2', color='maroon',  marker='inverted_triangle', size=6)
    fig_drc.line(   'time_s', 'delta_pulses_reed_1', source=cds, legend_label='delta reed 1', color='crimson')
    fig_drc.line(   'time_s', 'delta_pulses_reed_2', source=cds, legend_label='delta reed 2', color='maroon')

    # plot of flow rate
    fig_q = figure(title='Flow rate', x_axis_label='Time (s)', y_axis_label='Flow rate (m^3/h)', width=WIDTH, height=HEIGHT, toolbar_location='above')  # type: ignore [call-arg]
    fig_q.scatter('time_s', 'q_m3h', source=cds, color='black', marker='diamond')
    fig_q.line(   'time_s', 'q_m3h', source=cds, color='black')

    # plot of integral flow
    fig_iq = figure(title='Integral flow', x_axis_label='Time (s)', y_axis_label='Flow (m^3)', width=WIDTH, height=HEIGHT, toolbar_location='above')  # type: ignore [call-arg]
    fig_iq.scatter('time_s', 'integral_q_m3', source=cds, color='grey', marker='square', size=6)
    fig_iq.line(   'time_s', 'integral_q_m3', source=cds, color='grey')

    # create column plot
    col = column(
        fig_dt,
        fig_v,
        fig_dv,
        fig_rc,
        fig_drc,
        fig_q,
        fig_iq,
    )
    assert hasattr(col.children[0], 'x_range')  # for MyPy
    shared_x_range = col.children[0].x_range
    for f in col.children[1:]:
        assert hasattr(f, 'x_range')  # for MyPy
        f.x_range = shared_x_range

    # return column plot
    return col


def save_column_plot_as_html(col: Column, dst_dir_path: Path | str, open_: bool = False) -> str:
    html_str = file_html(col, CDN)
    html_file_path = Path(dst_dir_path) / PLOT_HTML_FILE_NAME
    html_file_path.write_text(html_str)
    if open_:
        wb_open_new_tab(str(html_file_path))
    return html_str


def plot_gv_sampling(gv_sampling_dir_path: Path | str, open_: bool = False) -> tuple[pl.DataFrame, Column]:
    # get data
    gv_sampling_dir_path = Path(gv_sampling_dir_path)
    df = get_df(gv_sampling_dir_path)
    # create, save, open, and return column plot
    col = create_column_plot(df)
    save_column_plot_as_html(col, gv_sampling_dir_path, open_)
    return df, col


###################
#    SCRIPTING    #
###################

def create_argparser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument('-d', '--gv-sampling-dir-path', type=Path, required=True, help='GasViewer data directory path.')
    parser.add_argument('-o', '--open', action='store_true', help='Open the plot in the browser (default: False).')
    return parser


def parse_args() -> Namespace:
    parser = create_argparser()
    args = parser.parse_args()
    return args


def main() -> None:
    args = parse_args()
    plot_gv_sampling(args.gv_sampling_dir_path, args.open)


if __name__ == '__main__':
    main()
