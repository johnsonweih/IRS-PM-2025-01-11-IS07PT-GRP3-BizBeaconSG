import React, { useState, useEffect } from 'react';
import './LinkPreview.css';

const LinkPreview = ({ url }) => {
  const [metadata, setMetadata] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const response = await fetch('http://localhost:4000/api/metadata', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ url }),
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch property data');
        }
        
        const data = await response.json();
        setMetadata(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchMetadata();
  }, [url]);

  const handleImageError = () => {
    setImageError(true);
  };

  if (loading) {
    return (
      <div className="link-preview">
        <div className="link-preview-card">
          <div className="link-preview-content">
            <p>Loading property information...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="link-preview">
        <div className="link-preview-card">
          <div className="link-preview-content">
            <p>Failed to load property information</p>
          </div>
        </div>
      </div>
    );
  }

  if (!metadata) {
    return null;
  }

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-SG', {
      style: 'currency',
      currency: 'SGD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(price);
  };

  const formatArea = (area) => {
    return new Intl.NumberFormat('en-SG', {
      style: 'decimal',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(area) + ' sqft';
  };

  return (
    <div>
      <a href={metadata.listing_url || url} target="_blank" rel="noopener noreferrer" className="link-preview-card">
        {metadata.image && !imageError && (
          <div className="link-preview-image">
            <img 
              src={metadata.image} 
              alt={metadata.title} 
              onError={handleImageError}
              loading="lazy"
            />
          </div>
        )}
        <div className="link-preview-content">
          <div className="link-preview-header">
            <h3 className="link-preview-title">{metadata.address}</h3>
            <div className="link-preview-price"></div>
          </div>
          
          <div className="link-preview-details">
            <div className="link-preview-detail">
              <span className="detail-label"></span>
              <span className="detail-value">{formatPrice(metadata.price)}</span>
            </div>
          </div>

          {metadata.description && (
            <p className="link-preview-description">{metadata.description}</p>
          )}
        </div>
      </a>
    </div>
  );
};

export default LinkPreview; 