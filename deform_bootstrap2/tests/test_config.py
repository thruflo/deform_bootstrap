from mock import Mock


def test_config_searchpath():
    config = Mock()
    config.add_static_view = Mock()
    from deform_bootstrap2 import includeme
    includeme(config)
    config.add_static_view.assert_called_once_with('static-deform_bootstrap2', 'deform_bootstrap2:static')
