import React, { Component, useState } from 'react';
import axios from 'axios';
import {APIProvider, Map, Marker } from '@vis.gl/react-google-maps';
import './App.css';

class App extends Component {
  constructor(){
    super()
    this.state = {
      countries : []
    }
  } 

  componentDidMount() {
    this.fetchCountries()
  }

  fetchCountries = async () => {
    const { data } = await axios.get(
      `${process.env.REACT_APP_API_URL}/malaria`,
      {
        params: {
          _limit: 10
         }
      }
    );
    const { countries } = data;
    this.setState({countries: data});
  }

  render() {
    const position = {lat: 53.54992, lng: 10.00678};
    const { countries } = this.state;

    return (
      <APIProvider apiKey={'AIzaSyCGKVsSrX_rsbwlEgWPcECBhUEErHOTDjM'}>
        <Map center={position} zoom={5}>

        {countries?.map(country => (
          <Marker position={{ lat: country.latlng[0], lng: country.latlng[1] }} />
        ))}       
        </Map>
        
      </APIProvider>
    );
  }
}

export default App;
