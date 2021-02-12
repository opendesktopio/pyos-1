#!/usr/bin/env python3
#
# Software Name : abcdesktop.io
# Version: 0.2
# SPDX-FileCopyrightText: Copyright (c) 2020-2021 Orange
# SPDX-License-Identifier: GPL-2.0-only
#
# This software is distributed under the GNU General Public License v2.0 only
# see the "license.txt" file for more details.
#
# Author: abcdesktop.io team
# Software description: cloud native desktop service
# 

import logging
import oc.od.settings as settings
import base64
import binascii
import oc.od.locator
import oc.auth.authservice

from oc.cherrypy    import Results,getclientipaddr
from oc.od.services import services

logger = logging.getLogger(__name__)

def getlocation(auth):
    logger.debug('')
    
    location = {}
    clientip = getclientipaddr()
    serverip = settings.default_server_ipaddr

    locatorPrivateActiveDirectory = None
    try:                        
        domain = auth.data.get('domain')
        if type(domain) is str:
            logger.debug( 'domain is %s', domain )
            # oc.od.services.services.locatorPrivateActiveDirectory is a dict
            # the key is the domain, and it contains all sites cached values
            locatorPrivateActiveDirectory = oc.od.services.services.locatorPrivateActiveDirectory.get(domain)            
    except Exception as e:
        logger.debug( e )


    # 'user' entry in the location dict
    # is the current user location
    location['user'] = oc.od.locator.resolvlocation(    ipAddr=clientip, 
                                                        locatorPublicInternet=services.locatorPublicInternet,
                                                        locatorPrivateActiveDirectory=locatorPrivateActiveDirectory)               
    # 'server' in the location dict
    # is the current desktop server location 
    location['server'] = oc.od.locator.resolvlocation(  ipAddr=serverip,  
                                                        locatorPublicInternet=services.locatorPublicInternet,
                                                        locatorPrivateActiveDirectory=locatorPrivateActiveDirectory)

    return location


def whoami(auth, user):
    """[whoami] getuserinfo for the current user request

    Args:
        auth (AuthInfo): authentification data
        user (AuthUser): user data 

    Returns:
        [dict]: userinfo dict entries 
            'sessionid',
            'userid',             
            'name',               
            'photo',            
            'provider',          
            'provider_type',     
            'target_ip',        
            'container_id',     
            'hostedby'         
    """
    logger.debug('')  

    # return default value
    userinfo = {
        'sessionid':        'jwt_token',
        'userid':           None,  
        'name':             None,  
        'photo':            None,
        'provider':         None, 
        'provider_type':    None, 
        'target_ip':        None,
        'container_id':     None,
        'hostedby':         None
    }

    # check if auth and user are correct type class
    if type(auth) is not oc.auth.authservice.AuthInfo or type(user) is not oc.auth.authservice.AuthUser :
        return userinfo

    userinfo['provider'] = auth.provider
    userinfo['providertype'] = auth.providertype
    userinfo['userid'] = user.get('userid')
    userinfo['name'] = user.get('name')
        
    completeuserinfo = oc.od.composer.getsecretuserinfo( auth, user  )
    if type(completeuserinfo) is dict:
        if completeuserinfo.get('type') == 'abcdesktop/ldif':
            data = completeuserinfo.get( 'data')
            if type(data) is dict:
                userphoto = None
                userinfo['photo'] = None
                # try to read photo
                # If LDAP attribut name is jpegPhoto
                # https://tools.ietf.org/html/rfc2798

                userphotoattributname = None
                if auth.providertype == 'ldap':
                    userphotoattributname = 'jpegPhoto'
                
                # If Active Directory attribut name is thumbnailPhoto
                if auth.providertype == 'activedirectory':
                    userphotoattributname = 'thumbnailPhoto'

                if userphotoattributname is not None:    
                    userphoto = data.get( userphotoattributname )
                    # if the photo is defined on user directory service
                    if userphoto is not None:
                        # check if userphoto is on base64 format
                        try:
                            # try to decode to detecte image format 
                            base64.b64decode(userphoto, validate=True)
                            # decode works: this photo is already base64 format
                            userinfo['photo'] = userphoto
                        except binascii.Error:
                            try:
                                userinfo['photo'] = oc.od.secret.ODSecret.bytestob64( userphoto )
                            except Exception :
                                self.logger.error( 'Failed to encode user photo userid:%s name:%s attribut: %s', str(userinfo['userid']), str(userinfo['name'], userphotoattributname) )
                                pass

                userinfo['sn'] = data.get( 'sn' )
                userinfo['cn'] = data.get( 'cn' )
                userinfo['mail'] = data.get( 'mail' )
                userinfo['initials'] = data.get( 'initials' )
                userinfo['givenName'] = data.get( 'givenName' )
                userinfo['description'] = data.get( 'description' )

    desktop = oc.od.composer.finddesktop( auth, user  )
    # desktop can be None, if desktop is not yet created 
    if desktop :
        # filter and copy data from desktop to userinfo dict
        userinfo['target_ip'] = desktop.ipAddr
        userinfo['container_id'] = desktop.id 
        userinfo['hostedby'] = desktop.nodehostname

    return userinfo