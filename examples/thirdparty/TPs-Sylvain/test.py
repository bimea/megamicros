
%gui asyncio

import asyncio
def wait_for_change(widget, value):
    future = asyncio.Future()
    def getvalue(change):
        # make the new value available
        future.set_result(change.new)
        widget.unobserve(getvalue, value)
    widget.observe(getvalue, value)
    return future

from ipywidgets import IntSlider
slider = IntSlider()

async def f():
    for i in range(10):
        print('did work %s'%i)
        x = await wait_for_change(slider, 'value')
        print('async function continued with value %s'%x)
asyncio.ensure_future(f())

slider

