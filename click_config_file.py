import os
import click
import configobj
import functools


class configobj_provider:
    """
    A parser for configobj configuration files

    Parameters
    ----------
    unrepr : bool
        Controls whether the file should be parsed using configobj's unrepr
        mode. Defaults to `True`.
    section : str
        If this is set to something other than the default of `None`, the
        provider will look for a corresponding section inside the
        configuration file and return only the values from that section.
    """
    

    def __init__(self, unrepr=True, section=None):
        self.unrepr = unrepr
        self.section = section
    

    def __call__(self, file_path, cmd_name):
        """
        Parse and return the configuration parameters.
    
        Parameters
        ----------
        file_path : str
            The path to the configuration file
        cmd_name : str
            The name of the click command

        Returns
        -------
        dict
            A dictionary containing the configuration parameters.
        """
        config = configobj.ConfigObj(file_path, unrepr=self.unrepr)
        if self.section:
            config = config[self.section].dict()
        return config


def configuration_option_base(*param_decls, **attrs):
    """
    Adds configuration file support to a click application.

    This will create an option of type `click.File` expecting the path to a
    configuration file. When specified, it overwrites the default values for
    all other click arguments or options with the corresponding value from the
    configuration file.

    The default name of the option is `--config`.
    By default, the configuration will be read from a configuration directory
    as determined by `click.get_app_dir`.

    This decorator accepts the same arguments as `click.option` and
    `click.Path`. In addition, the following keyword arguments are available:

    cmd_name : str
        The command name. This is used to determine the configuration
        directory. Defaults to `ctx.info_name`
    config_file_name : str
        The name of the configuration file. Defaults to `config`
    provider : callable
        A callable that parses the configuration file and returns a dictionary
        of the configuration parameters. Will be called as
        `provider(file_path, cmd_name)`. Default: `configobj_provider()`

    """
    param_decls = param_decls or ('--config', )
    option_name = param_decls[0]

    def decorator(f):

        def callback(cmd_name, config_file_name, saved_callback, provider, ctx,
                     param, value):
            # nonlocal cmd_name, config_file_name, saved_callback, provider
            if not ctx.default_map:
                ctx.default_map = {}
            if not cmd_name:
                cmd_name = ctx.info_name


            default_value = os.path.join(
                click.get_app_dir(cmd_name), config_file_name)
            param.default = default_value
            if not value:
                value = default_value
            try:
                config = provider(value, cmd_name)
            except Exception as e:
                raise click.BadOptionUsage(option_name,
                    "Error reading configuration file: {}".format(e), ctx)
            ctx.default_map.update(config)
            return saved_callback(ctx, param,
                                  value) if saved_callback else value

        attrs.setdefault('is_eager', True)
        attrs.setdefault('help', 'Read configuration from FILE.')
        attrs.setdefault('expose_value', False)
        cmd_name = attrs.pop('cmd_name', None)
        config_file_name = attrs.pop('config_file_name', None)
        provider = attrs.pop('provider', configobj_provider())
        path_default_params = {
            'exists': False,
            'file_okay': True,
            'dir_okay': False,
            'writable': False,
            'readable': True,
            'resolve_path': False
        }
        path_params = {
            k: attrs.pop(k, v)
            for k, v in path_default_params.items()
        }
        attrs['type'] = click.Path(**path_params)

        if config_file_name is not None:
            # Add callback only if config_file_name specified
            saved_callback = attrs.pop('callback', None)
            partial_callback = functools.partial(
                callback, cmd_name, config_file_name, saved_callback, provider)
            attrs['callback'] = partial_callback

        return click.option(*param_decls, **attrs)(f)

    return decorator


configuration_option = functools.partial(configuration_option_base, config_file_name='config')
configuration_option.__doc__ = """
Adds configuration file support to a click application.

Like `configuration_option_base` but with a default file name (`config`) for
the configuration file.  This causes the click application to search for the
configuration file in the standard location, even if the option is not
explicitly specified.
"""
